"""
Class that provides functions from a given SAM template
"""
import logging
import posixpath
from typing import Dict, List, Generator, Optional, cast, Tuple

from samcli.commands.local.cli_common.user_exceptions import InvalidLayerVersionArn
from samcli.lib.providers.exceptions import InvalidLayerReference
from samcli.lib.utils.colors import Colored
from samcli.lib.utils.packagetype import ZIP, IMAGE
from .provider import Function, LayerVersion, LocalBuildableStack
from .sam_base_provider import SamBaseProvider

LOG = logging.getLogger(__name__)


class SamFunctionProvider(SamBaseProvider):
    """
    Fetches and returns Lambda Functions from a SAM Template. The SAM template passed to this provider is assumed
    to be valid, normalized and a dictionary.

    It may or may not contain a function.
    """

    def __init__(self, stacks: List[LocalBuildableStack], ignore_code_extraction_warnings=False):
        """
        Initialize the class with SAM template data. The SAM template passed to this provider is assumed
        to be valid, normalized and a dictionary. It should be normalized by running all pre-processing
        before passing to this class. The process of normalization will remove structures like ``Globals``, resolve
        intrinsic functions etc.
        This class does not perform any syntactic validation of the template.

        After the class is initialized, any changes to the ``template_dict`` will not be reflected in here.
        You need to explicitly update the class with new template, if necessary.

        :param dict stacks: List of stacks functions are extracted from
        :param bool ignore_code_extraction_warnings: Ignores Log warnings
        """

        self.stack_and_resources: List[Tuple[LocalBuildableStack, Dict]] = [
            (
                stack,
                SamFunctionProvider.get_template(stack.template_dict, stack.parameters).get("Resources", {}),
            )
            for stack in stacks
        ]

        for stack, resources in self.stack_and_resources:
            LOG.debug("%d resources found in the stack %s", len(resources), stack.stack_path_for_children_resources)

        # Store a map of function name to function information for quick reference
        self.functions = self._extract_functions(self.stack_and_resources, ignore_code_extraction_warnings)

        self._deprecated_runtimes = {"nodejs4.3", "nodejs6.10", "nodejs8.10", "dotnetcore2.0"}
        self._colored = Colored()

    def get(self, name: str) -> Optional[Function]:
        """
        Returns the function given name or LogicalId of the function. Every SAM resource has a logicalId, but it may
        also have a function name. This method searches only for LogicalID and returns the function that matches.
        If it is in a nested stack, "name" can be prefixed with stack path to avoid ambiguity
        it.

        :param string name: Name of the function
        :return Function: namedtuple containing the Function information if function is found.
                          None, if function is not found
        :raises ValueError If name is not given
        """

        if not name:
            raise ValueError("Function name is required")

        for f in self.get_all():
            if posixpath.join(f.stack_path, f.name) == name or f.name == name:
                self._deprecate_notification(f.runtime)
                return f

            if posixpath.join(f.stack_path, f.functionname) == name or f.functionname == name:
                self._deprecate_notification(f.runtime)
                return f

        return None

    def _deprecate_notification(self, runtime: Optional[str]) -> None:
        if runtime in self._deprecated_runtimes:
            message = (
                f"WARNING: {runtime} is no longer supported by AWS Lambda, "
                "please update to a newer supported runtime. SAM CLI "
                f"will drop support for all deprecated runtimes {self._deprecated_runtimes} on May 1st. "
                "See issue: https://github.com/awslabs/aws-sam-cli/issues/1934 for more details."
            )
            LOG.warning(self._colored.yellow(message))

    def get_all(self) -> Generator[Function, None, None]:
        """
        Yields all the Lambda functions available in the SAM Template.

        :yields Function: namedtuple containing the function information
        """

        for _, function in self.functions.items():
            yield function

    @staticmethod
    def _extract_functions(
        resources_by_stack: List[Tuple[LocalBuildableStack, Dict]], ignore_code_extraction_warnings=False
    ) -> Dict[str, Function]:
        """
        Extracts and returns function information from the given dictionary of SAM/CloudFormation resources. This
        method supports functions defined with AWS::Serverless::Function and AWS::Lambda::Function

        :param dict resources_by_stack: Dictionary of SAM/CloudFormation resources by stack
        :param bool ignore_code_extraction_warnings: suppress log statements on code extraction from resources.
        :return dict(string : samcli.commands.local.lib.provider.Function): Dictionary of function LogicalId to the
            Function configuration object
        """

        result = {}
        for stack, resources in resources_by_stack:
            for name, resource in resources.items():

                resource_type = resource.get("Type")
                resource_properties = resource.get("Properties", {})
                resource_metadata = resource.get("Metadata", None)
                # Add extra metadata information to properties under a separate field.
                if resource_metadata:
                    resource_properties["Metadata"] = resource_metadata

                if resource_type == SamFunctionProvider.SERVERLESS_FUNCTION:
                    layers = SamFunctionProvider._parse_layer_info(
                        stack.stack_path_for_children_resources,
                        resource_properties.get("Layers", []),
                        resources,
                        ignore_code_extraction_warnings=ignore_code_extraction_warnings,
                    )
                    result[name] = SamFunctionProvider._convert_sam_function_resource(
                        stack.stack_path_for_children_resources,
                        name,
                        resource_properties,
                        layers,
                        ignore_code_extraction_warnings=ignore_code_extraction_warnings,
                    )

                elif resource_type == SamFunctionProvider.LAMBDA_FUNCTION:
                    layers = SamFunctionProvider._parse_layer_info(
                        stack.stack_path_for_children_resources,
                        resource_properties.get("Layers", []),
                        resources,
                        ignore_code_extraction_warnings=ignore_code_extraction_warnings,
                    )
                    result[name] = SamFunctionProvider._convert_lambda_function_resource(
                        stack.stack_path_for_children_resources, name, resource_properties, layers
                    )

                # We don't care about other resource types. Just ignore them

        return result

    @staticmethod
    def _convert_sam_function_resource(
        stack_path: str,
        name: str,
        resource_properties: Dict,
        layers: List[LayerVersion],
        ignore_code_extraction_warnings: bool = False,
    ) -> Function:
        """
        Converts a AWS::Serverless::Function resource to a Function configuration usable by the provider.

        Parameters
        ----------
        name str
            LogicalID of the resource NOTE: This is *not* the function name because not all functions declare a name
        resource_properties dict
            Properties of this resource
        layers List(samcli.commands.local.lib.provider.Layer)
            List of the Layer objects created from the template and layer list defined on the function.

        Returns
        -------
        samcli.commands.local.lib.provider.Function
            Function configuration
        """
        codeuri: Optional[str] = SamFunctionProvider.DEFAULT_CODEURI
        inlinecode = resource_properties.get("InlineCode")
        imageuri = None
        packagetype = resource_properties.get("PackageType", ZIP)
        if packagetype == ZIP:
            if inlinecode:
                LOG.debug("Found Serverless function with name='%s' and InlineCode", name)
                codeuri = None
            else:
                codeuri = SamFunctionProvider._extract_sam_function_codeuri(
                    name,
                    resource_properties,
                    "CodeUri",
                    ignore_code_extraction_warnings=ignore_code_extraction_warnings,
                )
                LOG.debug("Found Serverless function with name='%s' and CodeUri='%s'", name, codeuri)
        elif packagetype == IMAGE:
            imageuri = SamFunctionProvider._extract_sam_function_imageuri(resource_properties, "ImageUri")
            LOG.debug("Found Serverless function with name='%s' and ImageUri='%s'", name, imageuri)

        return SamFunctionProvider._build_function_configuration(
            stack_path, name, codeuri, resource_properties, layers, inlinecode, imageuri
        )

    @staticmethod
    def _convert_lambda_function_resource(
        stack_path: str, name: str, resource_properties: Dict, layers: List[LayerVersion]
    ) -> Function:
        """
        Converts a AWS::Lambda::Function resource to a Function configuration usable by the provider.

        Parameters
        ----------
        name str
            LogicalID of the resource NOTE: This is *not* the function name because not all functions declare a name
        resource_properties dict
            Properties of this resource
        layers List(samcli.commands.local.lib.provider.Layer)
            List of the Layer objects created from the template and layer list defined on the function.

        Returns
        -------
        samcli.commands.local.lib.provider.Function
            Function configuration
        """

        # CodeUri is set to "." in order to get code locally from current directory. AWS::Lambda::Function's ``Code``
        # property does not support specifying a local path
        codeuri: Optional[str] = SamFunctionProvider.DEFAULT_CODEURI
        inlinecode = None
        imageuri = None
        packagetype = resource_properties.get("PackageType", ZIP)
        if packagetype == ZIP:
            if (
                "Code" in resource_properties
                and isinstance(resource_properties["Code"], dict)
                and resource_properties["Code"].get("ZipFile")
            ):
                inlinecode = resource_properties["Code"]["ZipFile"]
                LOG.debug("Found Lambda function with name='%s' and Code ZipFile", name)
                codeuri = None
            else:
                codeuri = SamFunctionProvider._extract_lambda_function_code(resource_properties, "Code")
                LOG.debug("Found Lambda function with name='%s' and CodeUri='%s'", name, codeuri)
        elif packagetype == IMAGE:
            imageuri = SamFunctionProvider._extract_lambda_function_imageuri(resource_properties, "Code")
            LOG.debug("Found Lambda function with name='%s' and Imageuri='%s'", name, imageuri)

        return SamFunctionProvider._build_function_configuration(
            stack_path, name, codeuri, resource_properties, layers, inlinecode, imageuri
        )

    @staticmethod
    def _build_function_configuration(
        stack_path: str,
        name: str,
        codeuri: Optional[str],
        resource_properties: Dict,
        layers: List,
        inlinecode: Optional[str],
        imageuri: Optional[str],
    ) -> Function:
        """
        Builds a Function configuration usable by the provider.

        Parameters
        ----------
        name str
            LogicalID of the resource NOTE: This is *not* the function name because not all functions declare a name
        codeuri str
            Representing the local code path
        resource_properties dict
            Properties of this resource
        layers List(samcli.commands.local.lib.provider.Layer)
            List of the Layer objects created from the template and layer list defined on the function.

        Returns
        -------
        samcli.commands.local.lib.provider.Function
            Function configuration
        """
        return Function(
            stack_path=stack_path,
            name=name,
            functionname=resource_properties.get("FunctionName", name),
            packagetype=resource_properties.get("PackageType", ZIP),
            runtime=resource_properties.get("Runtime"),
            memory=resource_properties.get("MemorySize"),
            timeout=resource_properties.get("Timeout"),
            handler=resource_properties.get("Handler"),
            codeuri=codeuri,
            imageuri=imageuri if imageuri else resource_properties.get("ImageUri"),
            imageconfig=resource_properties.get("ImageConfig"),
            environment=resource_properties.get("Environment"),
            rolearn=resource_properties.get("Role"),
            events=resource_properties.get("Events"),
            layers=layers,
            metadata=resource_properties.get("Metadata", None),
            inlinecode=inlinecode,
            codesign_config_arn=resource_properties.get("CodeSigningConfigArn", None),
        )

    @staticmethod
    def _parse_layer_info(
        stack_path: str,
        list_of_layers: List[LayerVersion],
        resources: Dict,
        ignore_code_extraction_warnings: bool = False,
    ) -> List[LayerVersion]:
        """
        Creates a list of Layer objects that are represented by the resources and the list of layers

        Parameters
        ----------
        list_of_layers List(str)
            List of layers that are defined within the Layers Property on a function
        resources dict
            The Resources dictionary defined in a template

        Returns
        -------
        List(samcli.commands.local.lib.provider.Layer)
            List of the Layer objects created from the template and layer list defined on the function. The order
            of the layers does not change.

            I.E: list_of_layers = ["layer1", "layer2"] the return would be [Layer("layer1"), Layer("layer2")]
        """
        layers = []
        for layer in list_of_layers:
            if layer == "arn:aws:lambda:::awslayer:AmazonLinux1803":
                LOG.debug("Skipped arn:aws:lambda:::awslayer:AmazonLinux1803 as the containers are AmazonLinux1803")
                continue

            if layer == "arn:aws:lambda:::awslayer:AmazonLinux1703":
                raise InvalidLayerVersionArn(
                    "Building and invoking locally only supports AmazonLinux1803. See "
                    "https://aws.amazon.com/blogs/compute/upcoming-updates-to-the-aws-lambda-execution-environment/ "
                    "for more detials."
                )  # noqa: E501

            # If the layer is a string, assume it is the arn
            if isinstance(layer, str):
                layers.append(
                    LayerVersion(
                        layer,
                        None,
                        stack_path=stack_path,
                    )
                )
                continue

            # In the list of layers that is defined within a template, you can reference a LayerVersion resource.
            # When running locally, we need to follow that Ref so we can extract the local path to the layer code.
            if isinstance(layer, dict) and layer.get("Ref"):
                layer_logical_id = cast(str, layer.get("Ref"))
                layer_resource = resources.get(layer_logical_id)
                if not layer_resource or layer_resource.get("Type", "") not in (
                    SamFunctionProvider.SERVERLESS_LAYER,
                    SamFunctionProvider.LAMBDA_LAYER,
                ):
                    raise InvalidLayerReference()

                layer_properties = layer_resource.get("Properties", {})
                resource_type = layer_resource.get("Type")
                compatible_runtimes = layer_properties.get("CompatibleRuntimes")
                codeuri = None

                if resource_type == SamFunctionProvider.LAMBDA_LAYER:
                    codeuri = SamFunctionProvider._extract_lambda_function_code(layer_properties, "Content")

                if resource_type == SamFunctionProvider.SERVERLESS_LAYER:
                    codeuri = SamFunctionProvider._extract_sam_function_codeuri(
                        layer_logical_id, layer_properties, "ContentUri", ignore_code_extraction_warnings
                    )

                layers.append(
                    LayerVersion(
                        layer_logical_id,
                        codeuri,
                        compatible_runtimes,
                        layer_resource.get("Metadata", None),
                        stack_path=stack_path,
                    )
                )

        return layers

    def get_resources_by_stack_path(self, stack_path: str) -> Dict:
        candidates = [
            resources
            for stack, resources in self.stack_and_resources
            if stack.stack_path_for_children_resources == stack_path
        ]
        if not candidates:
            raise RuntimeError(f"Cannot find resources with stack_path = {stack_path}")
        return candidates[0]
