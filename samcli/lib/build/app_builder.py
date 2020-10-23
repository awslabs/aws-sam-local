"""
Builds the application
"""

import os
import io
import json
import logging
import pathlib
import shutil

import docker
from aws_lambda_builders.builder import LambdaBuilder
from aws_lambda_builders.exceptions import LambdaBuilderError
from aws_lambda_builders import RPC_PROTOCOL_VERSION as lambda_builders_protocol_version

import samcli.lib.utils.osutils as osutils
from samcli.lib.utils.colors import Colored
from samcli.commands.build.exceptions import MissingBuildMethodException
from samcli.lib.providers.sam_base_provider import SamBaseProvider
from samcli.lib.build.build_graph import FunctionBuildDefinition, LayerBuildDefinition, BuildGraph
from samcli.local.docker.lambda_build_container import LambdaBuildContainer
from .workflow_config import get_workflow_config, get_layer_subfolder, supports_build_in_container
from ..utils.hash import dir_checksum

LOG = logging.getLogger(__name__)


class UnsupportedBuilderLibraryVersionError(Exception):

    def __init__(self, container_name, error_msg):
        msg = "You are running an outdated version of Docker container '{container_name}' that is not compatible with" \
              "this version of SAM CLI. Please upgrade to continue to continue with build. Reason: '{error_msg}'"
        Exception.__init__(self, msg.format(container_name=container_name, error_msg=error_msg))


class ContainerBuildNotSupported(Exception):
    pass


class BuildError(Exception):

    def __init__(self, wrapped_from, msg):
        self.wrapped_from = wrapped_from
        Exception.__init__(self, msg)


class BuildInsideContainerError(Exception):
    pass


class ApplicationBuilder:
    """
    Class to build an entire application. Currently, this class builds Lambda functions only, but there is nothing that
    is stopping this class from supporting other resource types. Building in context of Lambda functions refer to
    converting source code into artifacts that can be run on AWS Lambda
    """

    def __init__(self,
                 resources_to_build,
                 build_dir,
                 base_dir,
                 cache_dir,
                 cached=False,
                 is_building_specific_resource=False,
                 manifest_path_override=None,
                 container_manager=None,
                 parallel=False,
                 mode=None):
        """
        Initialize the class

        Parameters
        ----------
        resources_to_build: Iterator
            Iterator that can vend out resources available in the SAM template

        build_dir : str
            Path to the directory where we will be storing built artifacts

        base_dir : str
            Path to a folder. Use this folder as the root to resolve relative source code paths against

        cache_dir : str
            Path to a the directory where we will be caching built artifacts

        cached:
            Optional. Set to True to build each function with cache to improve performance

        is_building_specific_resource : boolean
            Whether customer requested to build a specific resource alone in isolation,
            by specifying function_identifier to the build command.
            Ex: sam build MyServerlessFunction

        container_manager : samcli.local.docker.manager.ContainerManager
            Optional. If provided, we will attempt to build inside a Docker Container

        parallel : bool
            Optional. Set to True to build each function in parallel to improve performance

        mode : str
            Optional, name of the build mode to use ex: 'debug'
        """
        self._resources_to_build = resources_to_build
        self._build_dir = build_dir
        self._base_dir = base_dir
        self._cache_dir = cache_dir
        self._cached = cached
        self._manifest_path_override = manifest_path_override
        self._is_building_specific_resource = is_building_specific_resource

        self._container_manager = container_manager
        self._parallel = parallel
        self._mode = mode

        self._deprecated_runtimes = {"nodejs4.3", "nodejs6.10", "nodejs8.10", "dotnetcore2.0"}
        self._colored = Colored()

    def build(self):
        """
        Build the entire application

        Returns
        -------
        dict
            Returns the path to where each resource was built as a map of resource's LogicalId to the path string
        """
        build_graph = self._get_build_graph()
        result = self._build_functions(build_graph)
        result.update(self._build_layers(build_graph))

        # clean the redundant cached folder
        if self._cached:
            build_graph.clean_redundant_definitions_and_update(not self._is_building_specific_resource)
            uuids = {bd.uuid for bd in build_graph.get_function_build_definitions()}
            uuids.update({ld.uuid for ld in build_graph.get_layer_build_definitions()})
            for cache_dir in pathlib.Path(self._cache_dir).iterdir():
                if cache_dir.name not in uuids:
                    shutil.rmtree(pathlib.Path(self._cache_dir, cache_dir.name))

        return result

    def _get_build_graph(self):
        """
        Converts list of functions and layers into a build graph, where we can iterate on each unique build and trigger
        build
        :return: BuildGraph, which represents list of unique build definitions
        """
        build_graph = BuildGraph(self._build_dir)
        functions = self._resources_to_build.functions
        layers = self._resources_to_build.layers
        for function in functions:
            function_build_details = FunctionBuildDefinition(function.runtime, function.codeuri, function.metadata)
            build_graph.put_function_build_definition(function_build_details, function)

        for layer in layers:
            layer_build_details = LayerBuildDefinition(layer.name, layer.codeuri, layer.build_method, layer.compatible_runtimes)
            build_graph.put_layer_build_definition(layer_build_details, layer)

        build_graph.clean_redundant_definitions_and_update(not self._is_building_specific_resource)
        return build_graph

    def _build_functions(self, build_graph):
        """
        Iterates through build graph and runs each unique build and copies outcome to the corresponding function folder
        """
        function_build_results = {}

        if self._cached:
            build_function = self._build_unique_definition_cached
        else:
            build_function = self._build_unique_definition

        for build_definition in build_graph.get_function_build_definitions():
            function_build_results.update(build_function(build_definition))

        return function_build_results

    def _build_unique_definition_cached(self, build_definition):
        """
        If the build for a unique definition was cached before and the source code is not changed, copy the build
        artifact directly to the corresponding function folders with the same unique definition
        Else start a clean build and copy the build artifact directly to all paths with the same unique definition, as
        well as cache the build
        """
        code_dir = str(pathlib.Path(self._base_dir, build_definition.codeuri).resolve())
        source_md5 = dir_checksum(code_dir)
        cache_function_dir = pathlib.Path(self._cache_dir, build_definition.get_uuid())
        function_build_results = {}

        if not cache_function_dir.exists() or build_definition.get_source_md5() != source_md5:
            LOG.info("Cache is invalid, running build and copying resources to function build definition of %s",
                     build_definition.get_uuid())
            build_result = self._build_unique_definition(build_definition)
            function_build_results.update(build_result)

            if cache_function_dir.exists():
                shutil.rmtree(str(cache_function_dir))

            build_definition.set_source_md5(source_md5)
            for _, value in build_result.items():
                osutils.copytree(value, cache_function_dir)
                break
        else:
            LOG.info("Valid cache found, copying previously built resources from function build definition of %s",
                     build_definition.get_uuid())
            for function in build_definition.functions:
                # artifacts directory will be created by the builder
                artifacts_dir = str(pathlib.Path(self._build_dir, function.name))
                LOG.debug("Copying artifacts from %s to %s", cache_function_dir, artifacts_dir)
                osutils.copytree(cache_function_dir, artifacts_dir)
                function_build_results[function.name] = artifacts_dir

        return function_build_results

    def _build_unique_definition(self, build_definition):
        """
        Build the unique definition and then copy the artifact to the corresponding function folder
        """
        function_results = {}
        LOG.info("Building codeuri: %s runtime: %s metadata: %s functions: %s",
                 build_definition.codeuri, build_definition.runtime, build_definition.metadata,
                 [function.name for function in build_definition.functions])
        with osutils.mkdir_temp() as temporary_build_dir:
            LOG.debug("Building to following folder %s", temporary_build_dir)
            self._build_function(build_definition.get_function_name(),
                                 build_definition.codeuri,
                                 build_definition.runtime,
                                 build_definition.get_handler_name(),
                                 temporary_build_dir,
                                 build_definition.metadata)

            for function in build_definition.functions:
                # artifacts directory will be created by the builder
                artifacts_dir = str(pathlib.Path(self._build_dir, function.name))
                LOG.debug("Copying artifacts from %s to %s", temporary_build_dir, artifacts_dir)
                osutils.copytree(temporary_build_dir, artifacts_dir)
                function_results[function.name] = artifacts_dir
        return function_results

    def _build_layers(self, build_graph):
        """
        Iterates through build graph and runs each unique build and copies outcome to the corresponding layer folder
        """
        layer_build_results = {}

        if self._cached:
            build_layer = self._build_single_layer_definition_cached
        else:
            build_layer = self._build_single_layer_definition

        for layer_definition in build_graph.get_layer_build_definitions():
            layer_build_results.update(build_layer(layer_definition))

        return layer_build_results

    def _build_single_layer_definition_cached(self, layer_definition):
        """
        If the build for a unique definition was cached before and the source code is not changed, copy the build
        artifact directly to to the corresponding layer folder with the same unique definition
        Else start a clean build and copy the build artifact directly to the corresponding layer folder as well as
        cache the build
        """
        code_dir = str(pathlib.Path(self._base_dir, layer_definition.codeuri).resolve())
        source_md5 = dir_checksum(code_dir)
        cache_function_dir = pathlib.Path(self._cache_dir, layer_definition.get_uuid())
        layer_build_result = {}

        if not cache_function_dir.exists() or layer_definition.get_source_md5() != source_md5:
            LOG.info("Cache is invalid, running build and copying resources to layer build definition of %s",
                     layer_definition.get_uuid())
            build_result = self._build_single_layer_definition(layer_definition)
            layer_build_result.update(build_result)

            if cache_function_dir.exists():
                shutil.rmtree(str(cache_function_dir))

            layer_definition.set_source_md5(source_md5)
            for _, value in build_result.items():
                osutils.copytree(value, cache_function_dir)
                break
        else:
            LOG.info("Valid cache found, copying previously built resources from layer build definition of %s",
                     layer_definition.get_uuid())
            # artifacts directory will be created by the builder
            artifacts_dir = str(pathlib.Path(self._build_dir, layer_definition.layer.name))
            LOG.debug("Copying artifacts from %s to %s", cache_function_dir, artifacts_dir)
            osutils.copytree(cache_function_dir, artifacts_dir)
            layer_build_result[layer_definition.layer.name] = artifacts_dir

        return layer_build_result

    def _build_single_layer_definition(self, layer_definition):
        """
        Build the unique definition and then copy the artifact to the corresponding layer folder
        """
        layer = layer_definition.layer
        LOG.info("Building layer '%s'", layer.name)
        if layer.build_method is None:
            raise MissingBuildMethodException(
                f"Layer {layer.name} cannot be build without BuildMethod. Please provide BuildMethod in Metadata.")
        return {layer.name: self._build_layer(layer.name,
                                               layer.codeuri,
                                               layer.build_method,
                                               layer.compatible_runtimes)}

    def update_template(self, template_dict, original_template_path, built_artifacts):
        """
        Given the path to built artifacts, update the template to point appropriate resource CodeUris to the artifacts
        folder

        Parameters
        ----------
        template_dict
        original_template_path : str
            Path where the template file will be written to

        built_artifacts : dict
            Map of LogicalId of a resource to the path where the the built artifacts for this resource lives

        Returns
        -------
        dict
            Updated template
        """

        original_dir = os.path.dirname(original_template_path)

        for logical_id, resource in template_dict.get("Resources", {}).items():

            if logical_id not in built_artifacts:
                # this resource was not built. So skip it
                continue

            # Artifacts are written relative  the template because it makes the template portable
            #   Ex: A CI/CD pipeline build stage could zip the output folder and pass to a
            #   package stage running on a different machine
            artifact_relative_path = os.path.relpath(built_artifacts[logical_id], original_dir)

            resource_type = resource.get("Type")
            properties = resource.setdefault("Properties", {})
            if resource_type == SamBaseProvider.SERVERLESS_FUNCTION:
                properties["CodeUri"] = artifact_relative_path

            if resource_type == SamBaseProvider.LAMBDA_FUNCTION:
                properties["Code"] = artifact_relative_path

            if resource_type in [SamBaseProvider.SERVERLESS_LAYER, SamBaseProvider.LAMBDA_LAYER]:
                properties["ContentUri"] = artifact_relative_path

        return template_dict

    def _build_layer(self, layer_name, codeuri, specified_workflow, compatible_runtimes):
        # Create the arguments to pass to the builder
        # Code is always relative to the given base directory.
        code_dir = str(pathlib.Path(self._base_dir, codeuri).resolve())

        config = get_workflow_config(None, code_dir, self._base_dir, specified_workflow)
        subfolder = get_layer_subfolder(specified_workflow)

        # artifacts directory will be created by the builder
        artifacts_dir = str(pathlib.Path(self._build_dir, layer_name, subfolder))

        with osutils.mkdir_temp() as scratch_dir:
            manifest_path = self._manifest_path_override or os.path.join(code_dir, config.manifest_name)

            # By default prefer to build in-process for speed
            build_runtime = specified_workflow
            build_method = self._build_function_in_process
            if self._container_manager:
                build_method = self._build_function_on_container
                if config.language == "provided":
                    LOG.warning(
                        "For container layer build, first compatible runtime is chosen as build target for container.")
                    # Only set to this value if specified workflow is makefile which will result in config language as provided
                    build_runtime = compatible_runtimes[0]
            options = ApplicationBuilder._get_build_options(layer_name, config.language, None)

            build_method(config,
                         code_dir,
                         artifacts_dir,
                         scratch_dir,
                         manifest_path,
                         build_runtime,
                         options)
            # Not including subfolder in return so that we copy subfolder, instead of copying artifacts inside it.
            return str(pathlib.Path(self._build_dir, layer_name))

    def _build_function(self, function_name, codeuri, runtime, handler, artifacts_dir, metadata=None):
        """
        Given the function information, this method will build the Lambda function. Depending on the configuration
        it will either build the function in process or by spinning up a Docker container.

        Parameters
        ----------
        function_name : str
            Name or LogicalId of the function

        codeuri : str
            Path to where the code lives

        runtime : str
            AWS Lambda function runtime

        artifacts_dir: str
            Path to where function will be build into

        metadata : dict
            AWS Lambda function metadata

        Returns
        -------
        str
            Path to the location where built artifacts are available
        """

        if runtime in self._deprecated_runtimes:
            message = f"WARNING: {runtime} is no longer supported by AWS Lambda, please update to a newer supported runtime. SAM CLI " \
                      f"will drop support for all deprecated runtimes {self._deprecated_runtimes} on May 1st. " \
                      f"See issue: https://github.com/awslabs/aws-sam-cli/issues/1934 for more details."
            LOG.warning(self._colored.yellow(message))

        # Create the arguments to pass to the builder
        # Code is always relative to the given base directory.
        code_dir = str(pathlib.Path(self._base_dir, codeuri).resolve())

        # Determine if there was a build workflow that was specified directly in the template.
        specified_build_workflow = metadata.get("BuildMethod", None) if metadata else None

        config = get_workflow_config(runtime, code_dir, self._base_dir, specified_workflow=specified_build_workflow)

        with osutils.mkdir_temp() as scratch_dir:
            manifest_path = self._manifest_path_override or os.path.join(code_dir, config.manifest_name)

            # By default prefer to build in-process for speed
            build_method = self._build_function_in_process
            if self._container_manager:
                build_method = self._build_function_on_container

            options = ApplicationBuilder._get_build_options(function_name, config.language, handler)

            return build_method(config,
                                code_dir,
                                artifacts_dir,
                                scratch_dir,
                                manifest_path,
                                runtime,
                                options)

    @staticmethod
    def _get_build_options(function_name, language, handler):
        """
        Parameters
        ----------
        function_name str
            currrent function resource name
        language str
            language of the runtime
        handler str
            Handler value of the Lambda Function Resource
        Returns
        -------
        dict
            Dictionary that represents the options to pass to the builder workflow or None if options are not needed
        """

        _build_options = {
            'go': {'artifact_executable_name': handler},
            'provided': {'build_logical_id': function_name}
        }
        return _build_options.get(language, None)

    def _build_function_in_process(self,
                                   config,
                                   source_dir,
                                   artifacts_dir,
                                   scratch_dir,
                                   manifest_path,
                                   runtime,
                                   options):

        builder = LambdaBuilder(language=config.language,
                                dependency_manager=config.dependency_manager,
                                application_framework=config.application_framework)

        runtime = runtime.replace(".al2", "")

        try:
            builder.build(source_dir,
                          artifacts_dir,
                          scratch_dir,
                          manifest_path,
                          runtime=runtime,
                          executable_search_paths=config.executable_search_paths,
                          mode=self._mode,
                          options=options)
        except LambdaBuilderError as ex:
            raise BuildError(wrapped_from=ex.__class__.__name__, msg=str(ex))

        return artifacts_dir

    def _build_function_on_container(self,  # pylint: disable=too-many-locals
                                     config,
                                     source_dir,
                                     artifacts_dir,
                                     scratch_dir,
                                     manifest_path,
                                     runtime,
                                     options):

        if not self._container_manager.is_docker_reachable:
            raise BuildInsideContainerError(
                "Docker is unreachable. Docker needs to be running to build inside a container.")

        container_build_supported, reason = supports_build_in_container(config)
        if not container_build_supported:
            raise ContainerBuildNotSupported(reason)

        # If we are printing debug logs in SAM CLI, the builder library should also print debug logs
        log_level = LOG.getEffectiveLevel()

        container = LambdaBuildContainer(lambda_builders_protocol_version,
                                         config.language,
                                         config.dependency_manager,
                                         config.application_framework,
                                         source_dir,
                                         manifest_path,
                                         runtime,
                                         log_level=log_level,
                                         optimizations=None,
                                         options=options,
                                         executable_search_paths=config.executable_search_paths,
                                         mode=self._mode)

        try:
            try:
                self._container_manager.run(container)
            except docker.errors.APIError as ex:
                if "executable file not found in $PATH" in str(ex):
                    raise UnsupportedBuilderLibraryVersionError(container.image,
                                                                "{} executable not found in container"
                                                                .format(container.executable_name))

            # Container's output provides status of whether the build succeeded or failed
            # stdout contains the result of JSON-RPC call
            stdout_stream = io.BytesIO()
            # stderr contains logs printed by the builder. Stream it directly to terminal
            stderr_stream = osutils.stderr()
            container.wait_for_logs(stdout=stdout_stream, stderr=stderr_stream)

            stdout_data = stdout_stream.getvalue().decode('utf-8')
            LOG.debug("Build inside container returned response %s", stdout_data)

            response = self._parse_builder_response(stdout_data, container.image)

            # Request is successful. Now copy the artifacts back to the host
            LOG.debug("Build inside container was successful. Copying artifacts from container to host")

            # "/." is a Docker thing that instructions the copy command to download contents of the folder only
            result_dir_in_container = response["result"]["artifacts_dir"] + "/."
            container.copy(result_dir_in_container, artifacts_dir)
        finally:
            self._container_manager.stop(container)

        LOG.debug("Build inside container succeeded")
        return artifacts_dir

    @staticmethod
    def _parse_builder_response(stdout_data, image_name):

        try:
            response = json.loads(stdout_data)
        except Exception:
            # Invalid JSON is produced as an output only when the builder process crashed for some reason.
            # Report this as a crash
            LOG.debug("Builder crashed")
            raise

        if "error" in response:
            error = response.get("error", {})
            err_code = error.get("code")
            msg = error.get("message")

            if 400 <= err_code < 500:
                # Like HTTP 4xx - customer error
                raise BuildInsideContainerError(msg)

            if err_code == 505:
                # Like HTTP 505 error code: Version of the protocol is not supported
                # In this case, this error means that the Builder Library within the container is
                # not compatible with the version of protocol expected SAM CLI installation supports.
                # This can happen when customers have a newer container image or an older SAM CLI version.
                # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/505
                raise UnsupportedBuilderLibraryVersionError(image_name, msg)

            if err_code == -32601:
                # Default JSON Rpc Code for Method Unavailable https://www.jsonrpc.org/specification
                # This can happen if customers are using an incompatible version of builder library within the
                # container
                LOG.debug("Builder library does not support the supplied method")
                raise UnsupportedBuilderLibraryVersionError(image_name, msg)

            LOG.debug("Builder crashed")
            raise ValueError(msg)

        return response
