import sys
import os
import subprocess
import logging
from unittest import skipIf
from pathlib import Path
from parameterized import parameterized
<<<<<<< Updated upstream
import pytest
=======
from click.testing import CliRunner
from samcli.cli.main import cli

>>>>>>> Stashed changes

from .build_integ_base import BuildIntegBase
from tests.testing_utils import IS_WINDOWS, RUNNING_ON_CI, CI_OVERRIDE

import aws_lambda_builders.workflows.ruby_bundler.bundler as ruby_bundler_monkey


LOG = logging.getLogger(__name__)


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_PythonFunctions(BuildIntegBase):

    EXPECTED_FILES_GLOBAL_MANIFEST = set()
    EXPECTED_FILES_PROJECT_MANIFEST = {
        "__init__.py",
        "main.py",
        "numpy",
        # 'cryptography',
        "jinja2",
        "requirements.txt",
    }

    FUNCTION_LOGICAL_ID = "Function"

    @parameterized.expand(
        [
            ("python2.7", False),
            ("python3.6", False),
            ("python3.7", False),
            ("python2.7", "use_container"),
            ("python3.6", "use_container"),
            ("python3.7", "use_container"),
        ]
    )
    def test_with_default_requirements(self, runtime, use_container):

        # Don't run test on wrong Python versions
        py_version = self._get_python_version()
        if py_version != runtime:
            self.skipTest(
                "Current Python version '{}' does not match Lambda runtime version '{}'".format(py_version, runtime)
            )

        overrides = {"Runtime": runtime, "CodeUri": "Python", "Handler": "main.handler"}
        cmdlist = self.get_command_list(use_container=use_container, parameter_overrides=overrides)

        LOG.info("Running Command: {}", cmdlist)
        process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        process.wait()

        self._verify_built_artifact(
            self.default_build_dir, self.FUNCTION_LOGICAL_ID, self.EXPECTED_FILES_PROJECT_MANIFEST
        )

        self._verify_resource_property(
            str(self.built_template),
            "OtherRelativePathResource",
            "BodyS3Location",
            os.path.relpath(
                os.path.normpath(os.path.join(str(self.test_data_path), "SomeRelativePath")),
                str(self.default_build_dir),
            ),
        )

        expected = {"pi": "3.14", "jinja": "Hello World"}
        self._verify_invoke_built_function(
            self.built_template, self.FUNCTION_LOGICAL_ID, self._make_parameter_override_arg(overrides), expected
        )
        self.verify_docker_container_cleanedup(runtime)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files):

        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)

    def _get_python_version(self):
        return "python{}.{}".format(sys.version_info.major, sys.version_info.minor)


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_ErrorCases(BuildIntegBase):
    def test_unsupported_runtime(self):
        overrides = {"Runtime": "unsupportedpython", "CodeUri": "Python"}
        cmdlist = self.get_command_list(parameter_overrides=overrides)

        LOG.info("Running Command: {}", cmdlist)
        process = subprocess.Popen(cmdlist, cwd=self.working_dir, stdout=subprocess.PIPE)
        process.wait()

        process_stdout = b"".join(process.stdout.readlines()).strip().decode("utf-8")
        self.assertEqual(1, process.returncode)

        self.assertIn("Build Failed", process_stdout)


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_NodeFunctions(BuildIntegBase):

    EXPECTED_FILES_GLOBAL_MANIFEST = set()
    EXPECTED_FILES_PROJECT_MANIFEST = {"node_modules", "main.js"}
    EXPECTED_NODE_MODULES = {"minimal-request-promise"}

    FUNCTION_LOGICAL_ID = "Function"

    @parameterized.expand(
        [
            ("nodejs6.10", False),
            ("nodejs8.10", False),
            ("nodejs10.x", False),
            ("nodejs6.10", "use_container"),
            ("nodejs8.10", "use_container"),
            ("nodejs10.x", "use_container"),
        ]
    )
    def test_with_default_package_json(self, runtime, use_container):
        overrides = {"Runtime": runtime, "CodeUri": "Node", "Handler": "ignored"}
        cmdlist = self.get_command_list(use_container=use_container, parameter_overrides=overrides)

        LOG.info("Running Command: {}", cmdlist)
        process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        process.wait()

        self._verify_built_artifact(
            self.default_build_dir,
            self.FUNCTION_LOGICAL_ID,
            self.EXPECTED_FILES_PROJECT_MANIFEST,
            self.EXPECTED_NODE_MODULES,
        )

        self._verify_resource_property(
            str(self.built_template),
            "OtherRelativePathResource",
            "BodyS3Location",
            os.path.relpath(
                os.path.normpath(os.path.join(str(self.test_data_path), "SomeRelativePath")),
                str(self.default_build_dir),
            ),
        )
        self.verify_docker_container_cleanedup(runtime)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files, expected_modules):

        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)

        all_modules = set(os.listdir(str(resource_artifact_dir.joinpath("node_modules"))))
        actual_files = all_modules.intersection(expected_modules)
        self.assertEqual(actual_files, expected_modules)


class BundlerExecutionError(Exception):
    """
    Exception raised when Bundler fails.
    Will encapsulate error output from the command.
    """

    MESSAGE = "Bundler Failed: {message}"

    def __init__(self, **kwargs):
        Exception.__init__(self, self.MESSAGE.format(**kwargs))


class SubprocessBundler2(object):
    """
    Wrapper around the Bundler command line utility, encapsulating
    execution results.
    """

    def __init__(self, osutils, bundler_exe=None):
        self.osutils = osutils
        if bundler_exe is None:
            if osutils.is_windows():
                bundler_exe = 'bundler.bat'
            else:
                bundler_exe = 'bundle'

        self.bundler_exe = bundler_exe

    def run(self, args, cwd=None):
        if not isinstance(args, list):
            raise ValueError('args must be a list')

        if not args:
            raise ValueError('requires at least one arg')

        invoke_bundler = [self.bundler_exe] + args

        LOG.info("executing Bundler: %s", invoke_bundler)
        print(f"executing Bundler: {invoke_bundler}")

        p = self.osutils.popen(invoke_bundler,
                               stdout=self.osutils.pipe,
                               stderr=self.osutils.pipe,
                               cwd=cwd)

        out, err = p.communicate()

        LOG.info(f"STDOUT: {out.decode('utf8')}")
        LOG.info(f"STDERR: {err.decode('utf8')}")

        print(f"STDOUT: {out.decode('utf8')}")
        print(f"STDERR: {err.decode('utf8')}")

        if p.returncode != 0:
            raise BundlerExecutionError(message=err.decode('utf8').strip())

        return out.decode('utf8').strip()

@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_RubyFunctions(BuildIntegBase):

    EXPECTED_FILES_GLOBAL_MANIFEST = set()
    EXPECTED_FILES_PROJECT_MANIFEST = {"app.rb"}
    EXPECTED_RUBY_GEM = "aws-record"

    FUNCTION_LOGICAL_ID = "Function"

<<<<<<< Updated upstream
    @pytest.mark.flaky(reruns=3)
    @pytest.mark.timeout(timeout=300, method="thread")
    @parameterized.expand([("ruby2.5")])
    def test_building_ruby_in_container(self, runtime):
        self._test_with_default_gemfile(runtime, "use_container")

    @parameterized.expand([("ruby2.5")])
    def test_building_ruby_in_process(self, runtime):
        self._test_with_default_gemfile(runtime, False)

    def _test_with_default_gemfile(self, runtime, use_container):
=======
    @parameterized.expand([("ruby2.5", False)])
    def test_with_default_gemfile(self, runtime, use_container):
        ruby_bundler_monkey.SubprocessBundler.run = SubprocessBundler2.run
>>>>>>> Stashed changes
        overrides = {"Runtime": runtime, "CodeUri": "Ruby", "Handler": "ignored"}
        cmdlist = self.get_command_list(use_container=use_container, parameter_overrides=overrides)

        runner = CliRunner()
        result = runner.invoke(cli, cmdlist[1:])

        LOG.info(result.output)

        self.assertEquals(result.exit_code, 0)

        # LOG.info("Running Command: {}".format(cmdlist))
        # process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        # process.wait()
        #
        # self._verify_built_artifact(
        #     self.default_build_dir,
        #     self.FUNCTION_LOGICAL_ID,
        #     self.EXPECTED_FILES_PROJECT_MANIFEST,
        #     self.EXPECTED_RUBY_GEM,
        # )
        #
        # self._verify_resource_property(
        #     str(self.built_template),
        #     "OtherRelativePathResource",
        #     "BodyS3Location",
        #     os.path.relpath(
        #         os.path.normpath(os.path.join(str(self.test_data_path), "SomeRelativePath")),
        #         str(self.default_build_dir),
        #     ),
        # )
        # self.verify_docker_container_cleanedup(runtime)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files, expected_modules):

        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)

        ruby_version = None
        ruby_bundled_path = None

        # Walk through ruby version to get to the gem path
        for dirpath, dirname, _ in os.walk(str(resource_artifact_dir.joinpath("vendor", "bundle", "ruby"))):
            ruby_version = dirname
            ruby_bundled_path = Path(dirpath)
            break
        gem_path = ruby_bundled_path.joinpath(ruby_version[0], "gems")

        self.assertTrue(any([True if self.EXPECTED_RUBY_GEM in gem else False for gem in os.listdir(str(gem_path))]))


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_Java(BuildIntegBase):

    EXPECTED_FILES_PROJECT_MANIFEST_GRADLE = {"aws", "lib", "META-INF"}
    EXPECTED_FILES_PROJECT_MANIFEST_MAVEN = {"aws", "lib"}
    EXPECTED_DEPENDENCIES = {"annotations-2.1.0.jar", "aws-lambda-java-core-1.1.0.jar"}

    FUNCTION_LOGICAL_ID = "Function"
    USING_GRADLE_PATH = os.path.join("Java", "gradle")
    USING_GRADLEW_PATH = os.path.join("Java", "gradlew")
    USING_GRADLE_KOTLIN_PATH = os.path.join("Java", "gradle-kotlin")
    USING_MAVEN_PATH = os.path.join("Java", "maven")
    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"

    @pytest.mark.flaky(reruns=3)
    @pytest.mark.timeout(timeout=300, method="thread")
    @parameterized.expand(
        [
            ("java8", USING_GRADLE_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_GRADLEW_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_GRADLE_KOTLIN_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_MAVEN_PATH, EXPECTED_FILES_PROJECT_MANIFEST_MAVEN),
            ("java8", USING_GRADLE_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
        ]
    )
    def test_building_java_in_container(self, runtime, code_path, expected_files):
        self._test_with_building_java(runtime, code_path, expected_files, "use_container")

    @parameterized.expand(
        [
            ("java8", USING_GRADLE_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_GRADLEW_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_GRADLE_KOTLIN_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
            ("java8", USING_MAVEN_PATH, EXPECTED_FILES_PROJECT_MANIFEST_MAVEN),
            ("java8", USING_GRADLE_PATH, EXPECTED_FILES_PROJECT_MANIFEST_GRADLE),
        ]
    )
    def test_building_java_in_process(self, runtime, code_path, expected_files):
        self._test_with_building_java(runtime, code_path, expected_files, False)

    def _test_with_building_java(self, runtime, code_path, expected_files, use_container):
        overrides = {"Runtime": runtime, "CodeUri": code_path, "Handler": "aws.example.Hello::myHandler"}
        cmdlist = self.get_command_list(use_container=use_container, parameter_overrides=overrides)
        cmdlist += ["--skip-pull-image"]
        if code_path == self.USING_GRADLEW_PATH and use_container and IS_WINDOWS:
            self._change_to_unix_line_ending(os.path.join(self.test_data_path, self.USING_GRADLEW_PATH, "gradlew"))

        LOG.info("Running Command: {}".format(cmdlist))
        process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        process.wait()

        self._verify_built_artifact(
            self.default_build_dir, self.FUNCTION_LOGICAL_ID, expected_files, self.EXPECTED_DEPENDENCIES
        )

        self._verify_resource_property(
            str(self.built_template),
            "OtherRelativePathResource",
            "BodyS3Location",
            os.path.relpath(
                os.path.normpath(os.path.join(str(self.test_data_path), "SomeRelativePath")),
                str(self.default_build_dir),
            ),
        )

        # If we are testing in the container, invoke the function as well. Otherwise we cannot guarantee docker is on appveyor
        if use_container:
            expected = "Hello World"
            self._verify_invoke_built_function(
                self.built_template, self.FUNCTION_LOGICAL_ID, self._make_parameter_override_arg(overrides), expected
            )

            self.verify_docker_container_cleanedup(runtime)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files, expected_modules):

        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)

        lib_dir_contents = set(os.listdir(str(resource_artifact_dir.joinpath("lib"))))
        self.assertEqual(lib_dir_contents, expected_modules)

    def _change_to_unix_line_ending(self, path):
        with open(os.path.abspath(path), "rb") as open_file:
            content = open_file.read()

        content = content.replace(self.WINDOWS_LINE_ENDING, self.UNIX_LINE_ENDING)

        with open(os.path.abspath(path), "wb") as open_file:
            open_file.write(content)


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_Dotnet_cli_package(BuildIntegBase):

    FUNCTION_LOGICAL_ID = "Function"
    EXPECTED_FILES_PROJECT_MANIFEST = {
        "Amazon.Lambda.APIGatewayEvents.dll",
        "HelloWorld.pdb",
        "Amazon.Lambda.Core.dll",
        "HelloWorld.runtimeconfig.json",
        "Amazon.Lambda.Serialization.Json.dll",
        "Newtonsoft.Json.dll",
        "HelloWorld.deps.json",
        "HelloWorld.dll",
    }

    @parameterized.expand(
        [
            ("dotnetcore2.0", "Dotnetcore2.0", None),
            ("dotnetcore2.1", "Dotnetcore2.1", None),
            ("dotnetcore2.0", "Dotnetcore2.0", "debug"),
            ("dotnetcore2.1", "Dotnetcore2.1", "debug"),
        ]
    )
    def test_with_dotnetcore(self, runtime, code_uri, mode):
        overrides = {
            "Runtime": runtime,
            "CodeUri": code_uri,
            "Handler": "HelloWorld::HelloWorld.Function::FunctionHandler",
        }
        cmdlist = self.get_command_list(use_container=False, parameter_overrides=overrides)

        LOG.info("Running Command: {}".format(cmdlist))
        LOG.info("Running with SAM_BUILD_MODE={}".format(mode))

        newenv = os.environ.copy()
        if mode:
            newenv["SAM_BUILD_MODE"] = mode

        process = subprocess.Popen(cmdlist, cwd=self.working_dir, env=newenv)
        process.wait()

        self._verify_built_artifact(
            self.default_build_dir, self.FUNCTION_LOGICAL_ID, self.EXPECTED_FILES_PROJECT_MANIFEST
        )

        self._verify_resource_property(
            str(self.built_template),
            "OtherRelativePathResource",
            "BodyS3Location",
            os.path.relpath(
                os.path.normpath(os.path.join(str(self.test_data_path), "SomeRelativePath")),
                str(self.default_build_dir),
            ),
        )

        expected = "{'message': 'Hello World'}"
        self._verify_invoke_built_function(
            self.built_template, self.FUNCTION_LOGICAL_ID, self._make_parameter_override_arg(overrides), expected
        )

        self.verify_docker_container_cleanedup(runtime)

    @parameterized.expand([("dotnetcore2.0", "Dotnetcore2.0"), ("dotnetcore2.1", "Dotnetcore2.1")])
    def test_must_fail_with_container(self, runtime, code_uri):
        use_container = True
        overrides = {
            "Runtime": runtime,
            "CodeUri": code_uri,
            "Handler": "HelloWorld::HelloWorld.Function::FunctionHandler",
        }
        cmdlist = self.get_command_list(use_container=use_container, parameter_overrides=overrides)

        LOG.info("Running Command: {}".format(cmdlist))
        process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        process.wait()

        # Must error out, because container builds are not supported
        self.assertEqual(process.returncode, 1)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files):

        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)


@skipIf(
    ((IS_WINDOWS and RUNNING_ON_CI) and not CI_OVERRIDE),
    "Skip build tests on windows when running in CI unless overridden",
)
class TestBuildCommand_SingleFunctionBuilds(BuildIntegBase):
    template = "many-functions-template.yaml"

    EXPECTED_FILES_GLOBAL_MANIFEST = set()
    EXPECTED_FILES_PROJECT_MANIFEST = {
        "__init__.py",
        "main.py",
        "numpy",
        # 'cryptography',
        "jinja2",
        "requirements.txt",
    }

    def test_function_not_found(self):
        overrides = {"Runtime": "python3.7", "CodeUri": "Python", "Handler": "main.handler"}
        cmdlist = self.get_command_list(parameter_overrides=overrides, function_identifier="FunctionNotInTemplate")

        process = subprocess.Popen(cmdlist, cwd=self.working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        self.assertEqual(process.returncode, 1)
        self.assertIn("FunctionNotInTemplate not found", str(stderr.decode("utf8")))

    @parameterized.expand(
        [
            ("python3.7", False, "FunctionOne"),
            ("python3.7", "use_container", "FunctionOne"),
            ("python3.7", False, "FunctionTwo"),
            ("python3.7", "use_container", "FunctionTwo"),
        ]
    )
    def test_build_single_function(self, runtime, use_container, function_identifier):
        # Don't run test on wrong Python versions
        py_version = self._get_python_version()
        if py_version != runtime:
            self.skipTest(
                "Current Python version '{}' does not match Lambda runtime version '{}'".format(py_version, runtime)
            )

        overrides = {"Runtime": runtime, "CodeUri": "Python", "Handler": "main.handler"}
        cmdlist = self.get_command_list(
            use_container=use_container, parameter_overrides=overrides, function_identifier=function_identifier
        )

        LOG.info("Running Command: {}", cmdlist)
        process = subprocess.Popen(cmdlist, cwd=self.working_dir)
        process.wait()

        self._verify_built_artifact(self.default_build_dir, function_identifier, self.EXPECTED_FILES_PROJECT_MANIFEST)

        expected = {"pi": "3.14", "jinja": "Hello World"}
        self._verify_invoke_built_function(
            self.built_template, function_identifier, self._make_parameter_override_arg(overrides), expected
        )
        self.verify_docker_container_cleanedup(runtime)

    def _verify_built_artifact(self, build_dir, function_logical_id, expected_files):
        self.assertTrue(build_dir.exists(), "Build directory should be created")

        build_dir_files = os.listdir(str(build_dir))
        self.assertIn("template.yaml", build_dir_files)
        self.assertIn(function_logical_id, build_dir_files)

        template_path = build_dir.joinpath("template.yaml")
        resource_artifact_dir = build_dir.joinpath(function_logical_id)

        # Make sure the template has correct CodeUri for resource
        self._verify_resource_property(str(template_path), function_logical_id, "CodeUri", function_logical_id)

        all_artifacts = set(os.listdir(str(resource_artifact_dir)))
        actual_files = all_artifacts.intersection(expected_files)
        self.assertEqual(actual_files, expected_files)

    def _get_python_version(self):
        return "python{}.{}".format(sys.version_info.major, sys.version_info.minor)
