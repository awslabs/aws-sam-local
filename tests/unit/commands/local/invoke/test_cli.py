"""
Tests Local Invoke CLI
"""

from unittest import TestCase
from mock import patch, Mock
from parameterized import parameterized, param

from samcli.local.lambdafn.exceptions import FunctionNotFound
from samcli.commands.validate.lib.exceptions import InvalidSamDocumentException
from samcli.commands.exceptions import UserException
from samcli.commands.local.invoke.cli import do_cli as invoke_cli, _get_event as invoke_cli_get_event
from samcli.commands.local.lib.exceptions import OverridesNotWellDefinedError
from samcli.local.docker.manager import DockerImagePullFailedException, DockerContainerException


STDIN_FILE_NAME = "-"


class TestCli(TestCase):

    def setUp(self):
        self.function_id = "id"
        self.template = "template"
        self.eventfile = "eventfile"
        self.env_vars = "env-vars"
        self.debug_port = 123
        self.debug_args = "args"
        self.debugger_path = "/test/path"
        self.docker_volume_basedir = "basedir"
        self.docker_network = "network"
        self.log_file = "logfile"
        self.skip_pull_image = True
        self.profile = "profile"
        self.no_event = False
        self.region = "region"
        self.parameter_overrides = {}
        self.container_name = "container-name"

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_cli_must_setup_context_and_invoke(self, get_event_mock, InvokeContextMock):
        event_data = "data"
        get_event_mock.return_value = event_data

        # Mock the __enter__ method to return a object inside a context manager
        context_mock = Mock()
        InvokeContextMock.return_value.__enter__.return_value = context_mock

        invoke_cli(ctx=None,
                   function_identifier=self.function_id,
                   template=self.template,
                   event=self.eventfile,
                   no_event=self.no_event,
                   env_vars=self.env_vars,
                   debug_port=self.debug_port,
                   debug_args=self.debug_args,
                   debugger_path=self.debugger_path,
                   docker_volume_basedir=self.docker_volume_basedir,
                   docker_network=self.docker_network,
                   log_file=self.log_file,
                   skip_pull_image=self.skip_pull_image,
                   profile=self.profile,
                   region=self.region,
                   parameter_overrides=self.parameter_overrides,
                   container_name=self.container_name)

        InvokeContextMock.assert_called_with(template_file=self.template,
                                             function_identifier=self.function_id,
                                             env_vars_file=self.env_vars,
                                             docker_volume_basedir=self.docker_volume_basedir,
                                             docker_network=self.docker_network,
                                             log_file=self.log_file,
                                             skip_pull_image=self.skip_pull_image,
                                             aws_profile=self.profile,
                                             debug_port=self.debug_port,
                                             debug_args=self.debug_args,
                                             debugger_path=self.debugger_path,
                                             aws_region=self.region,
                                             parameter_overrides=self.parameter_overrides,
                                             container_name=self.container_name)

        context_mock.local_lambda_runner.invoke.assert_called_with(context_mock.function_name,
                                                                   event=event_data,
                                                                   stdout=context_mock.stdout,
                                                                   stderr=context_mock.stderr)
        get_event_mock.assert_called_with(self.eventfile)

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_cli_must_invoke_with_no_event(self, get_event_mock, InvokeContextMock):
        self.no_event = True
        # Mock the __enter__ method to return a object inside a context manager
        context_mock = Mock()
        InvokeContextMock.return_value.__enter__.return_value = context_mock
        invoke_cli(ctx=None,
                   function_identifier=self.function_id,
                   template=self.template,
                   event=STDIN_FILE_NAME,
                   no_event=self.no_event,
                   env_vars=self.env_vars,
                   debug_port=self.debug_port,
                   debug_args=self.debug_args,
                   debugger_path=self.debugger_path,
                   docker_volume_basedir=self.docker_volume_basedir,
                   docker_network=self.docker_network,
                   log_file=self.log_file,
                   skip_pull_image=self.skip_pull_image,
                   profile=self.profile,
                   region=self.region,
                   parameter_overrides=self.parameter_overrides,
                   container_name=self.container_name)

        InvokeContextMock.assert_called_with(template_file=self.template,
                                             function_identifier=self.function_id,
                                             env_vars_file=self.env_vars,
                                             docker_volume_basedir=self.docker_volume_basedir,
                                             docker_network=self.docker_network,
                                             log_file=self.log_file,
                                             skip_pull_image=self.skip_pull_image,
                                             aws_profile=self.profile,
                                             debug_port=self.debug_port,
                                             debug_args=self.debug_args,
                                             debugger_path=self.debugger_path,
                                             aws_region=self.region,
                                             parameter_overrides=self.parameter_overrides,
                                             container_name=self.container_name)

        context_mock.local_lambda_runner.invoke.assert_called_with(context_mock.function_name,
                                                                   event="{}",
                                                                   stdout=context_mock.stdout,
                                                                   stderr=context_mock.stderr)
        get_event_mock.assert_not_called()

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_must_raise_user_exception_on_no_event_and_event(self, get_event_mock, InvokeContextMock):
        self.no_event = True

        with self.assertRaises(UserException) as ex_ctx:

            invoke_cli(ctx=None,
                       function_identifier=self.function_id,
                       template=self.template,
                       event=self.eventfile,
                       no_event=self.no_event,
                       env_vars=self.env_vars,
                       debug_port=self.debug_port,
                       debug_args=self.debug_args,
                       debugger_path=self.debugger_path,
                       docker_volume_basedir=self.docker_volume_basedir,
                       docker_network=self.docker_network,
                       log_file=self.log_file,
                       skip_pull_image=self.skip_pull_image,
                       profile=self.profile,
                       region=self.region,
                       parameter_overrides=self.parameter_overrides,
                       container_name=self.container_name)

        msg = str(ex_ctx.exception)
        self.assertEquals(msg, "no_event and event cannot be used together. Please provide only one.")

    @parameterized.expand([
        param(FunctionNotFound("not found"), "Function id not found in template"),
        param(DockerImagePullFailedException("Failed to pull image"), "Failed to pull image")
    ])
    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_must_raise_user_exception_on_function_not_found(self,
                                                             side_effect_exception,
                                                             expected_exectpion_message,
                                                             get_event_mock,
                                                             InvokeContextMock):
        event_data = "data"
        get_event_mock.return_value = event_data

        # Mock the __enter__ method to return a object inside a context manager
        context_mock = Mock()
        InvokeContextMock.return_value.__enter__.return_value = context_mock

        context_mock.local_lambda_runner.invoke.side_effect = side_effect_exception

        with self.assertRaises(UserException) as ex_ctx:

            invoke_cli(ctx=None,
                       function_identifier=self.function_id,
                       template=self.template,
                       event=self.eventfile,
                       no_event=self.no_event,
                       env_vars=self.env_vars,
                       debug_port=self.debug_port,
                       debug_args=self.debug_args,
                       debugger_path=self.debugger_path,
                       docker_volume_basedir=self.docker_volume_basedir,
                       docker_network=self.docker_network,
                       log_file=self.log_file,
                       skip_pull_image=self.skip_pull_image,
                       profile=self.profile,
                       region=self.region,
                       parameter_overrides=self.parameter_overrides,
                       container_name=self.container_name)

        msg = str(ex_ctx.exception)
        self.assertEquals(msg, expected_exectpion_message)

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_must_raise_user_exception_on_invalid_sam_template(self, get_event_mock, InvokeContextMock):
        event_data = "data"
        get_event_mock.return_value = event_data

        InvokeContextMock.side_effect = InvalidSamDocumentException("bad template")

        with self.assertRaises(UserException) as ex_ctx:

            invoke_cli(ctx=None,
                       function_identifier=self.function_id,
                       template=self.template,
                       event=self.eventfile,
                       no_event=self.no_event,
                       env_vars=self.env_vars,
                       debug_port=self.debug_port,
                       debug_args=self.debug_args,
                       debugger_path=self.debugger_path,
                       docker_volume_basedir=self.docker_volume_basedir,
                       docker_network=self.docker_network,
                       log_file=self.log_file,
                       skip_pull_image=self.skip_pull_image,
                       profile=self.profile,
                       region=self.region,
                       parameter_overrides=self.parameter_overrides,
                       container_name=self.container_name)

        msg = str(ex_ctx.exception)
        self.assertEquals(msg, "bad template")

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_must_raise_user_exception_on_DockerContainerException(self, get_event_mock, InvokeContextMock):
        get_event_mock.return_value = "event_data"

        context_mock = Mock()
        InvokeContextMock.return_value.__enter__.return_value = context_mock

        context_mock.local_lambda_runner.invoke.side_effect = DockerContainerException("error")

        with self.assertRaises(UserException) as ex_ctx:

            invoke_cli(ctx=None,
                       function_identifier=self.function_id,
                       template=self.template,
                       event=self.eventfile,
                       no_event=self.no_event,
                       env_vars=self.env_vars,
                       debug_port=self.debug_port,
                       debug_args=self.debug_args,
                       debugger_path=self.debugger_path,
                       docker_volume_basedir=self.docker_volume_basedir,
                       docker_network=self.docker_network,
                       log_file=self.log_file,
                       skip_pull_image=self.skip_pull_image,
                       profile=self.profile,
                       region=self.region,
                       parameter_overrides=self.parameter_overrides,
                       container_name=self.container_name)

        self.assertEqual("error", str(ex_ctx.exception))

    @patch("samcli.commands.local.invoke.cli.InvokeContext")
    @patch("samcli.commands.local.invoke.cli._get_event")
    def test_must_raise_user_exception_on_invalid_env_vars(self, get_event_mock, InvokeContextMock):
        event_data = "data"
        get_event_mock.return_value = event_data

        InvokeContextMock.side_effect = OverridesNotWellDefinedError("bad env vars")

        with self.assertRaises(UserException) as ex_ctx:

            invoke_cli(ctx=None,
                       function_identifier=self.function_id,
                       template=self.template,
                       event=self.eventfile,
                       no_event=self.no_event,
                       env_vars=self.env_vars,
                       debug_port=self.debug_port,
                       debug_args=self.debug_args,
                       debugger_path=self.debugger_path,
                       docker_volume_basedir=self.docker_volume_basedir,
                       docker_network=self.docker_network,
                       log_file=self.log_file,
                       skip_pull_image=self.skip_pull_image,
                       profile=self.profile,
                       region=self.region,
                       parameter_overrides=self.parameter_overrides,
                       container_name=self.container_name)

        msg = str(ex_ctx.exception)
        self.assertEquals(msg, "bad env vars")


class TestGetEvent(TestCase):

    @parameterized.expand([
        param(STDIN_FILE_NAME),
        param("somefile")
    ])
    @patch("samcli.commands.local.invoke.cli.click")
    def test_must_work_with_stdin(self, filename, click_mock):
        event_data = "some data"

        # Mock file pointer
        fp_mock = Mock()

        # Mock the context manager
        click_mock.open_file.return_value.__enter__.return_value = fp_mock
        fp_mock.read.return_value = event_data

        result = invoke_cli_get_event(filename)

        self.assertEquals(result, event_data)
        fp_mock.read.assert_called_with()
