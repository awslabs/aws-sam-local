from unittest import TestCase
from unittest.mock import patch, call, ANY
from parameterized import parameterized, param

import click

from samcli.commands.deploy.guided_context import GuidedContext


class TestGuidedContext(TestCase):
    def setUp(self):
        self.gc = GuidedContext(
            template_file="template",
            stack_name="test",
            s3_bucket="s3_b",
            s3_prefix="s3_p",
            confirm_changeset=True,
            region="region",
        )

    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    @patch("samcli.commands.deploy.guided_context.signer_config_per_function")
    def test_guided_prompts_check_defaults_non_public_resources(
        self,
        patched_signer_config_per_function,
        patched_get_template_data,
        patchedauth_per_resource,
        patched_manage_stack,
        patched_confirm,
        patched_prompt,
    ):
        # Series of inputs to confirmations so that full range of questions are asked.
        patchedauth_per_resource.return_value = [
            ("HelloWorldFunction", True),
        ]
        patched_confirm.side_effect = [True, False, "", True]
        patched_manage_stack.return_value = "managed_s3_stack"
        patched_signer_config_per_function.return_value = ({}, {})
        self.gc.guided_prompts(parameter_override_keys=None)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        # Now to check for all the defaults on prompts.
        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    @patch("samcli.commands.deploy.guided_context.signer_config_per_function")
    def test_guided_prompts_check_defaults_public_resources(
        self,
        patched_signer_config_per_function,
        patched_get_template_data,
        patchedauth_per_resource,
        patched_manage_stack,
        patched_confirm,
        patched_prompt,
    ):
        # Series of inputs to confirmations so that full range of questions are asked.
        patchedauth_per_resource.return_value = [("HelloWorldFunction", False)]
        patched_confirm.side_effect = [True, False, True, False, ""]
        patched_manage_stack.return_value = "managed_s3_stack"
        patched_signer_config_per_function.return_value = ({}, {})
        self.gc.guided_prompts(parameter_override_keys=None)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(
                f"\t{self.gc.start_bold}HelloWorldFunction may not have authorization defined, Is this okay?{self.gc.end_bold}",
                default=False,
            ),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        # Now to check for all the defaults on prompts.
        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

    @parameterized.expand(
        [
            param((("CAPABILITY_IAM",),)),
            param((("CAPABILITY_AUTO_EXPAND",),)),
            param(
                (
                    (
                        "CAPABILITY_AUTO_EXPAND",
                        "CAPABILITY_IAM",
                    ),
                )
            ),
        ]
    )
    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    @patch("samcli.commands.deploy.guided_context.signer_config_per_function")
    def test_guided_prompts_with_given_capabilities(
        self,
        given_capabilities,
        patched_signer_config_per_function,
        patched_get_template_data,
        patchedauth_per_resource,
        patched_manage_stack,
        patched_confirm,
        patched_prompt,
    ):
        patched_signer_config_per_function.return_value = ({}, {})
        self.gc.capabilities = given_capabilities
        # Series of inputs to confirmations so that full range of questions are asked.
        patched_confirm.side_effect = [True, False, "", True]
        self.gc.guided_prompts(parameter_override_keys=None)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        # Now to check for all the defaults on prompts.
        expected_capabilities = list(given_capabilities[0])
        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=expected_capabilities, type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    def test_guided_prompts_check_configuration_file_prompt_calls(
        self, patched_get_template_data, patchedauth_per_resource, patched_manage_stack, patched_confirm, patched_prompt
    ):
        # Series of inputs to confirmations so that full range of questions are asked.
        patchedauth_per_resource.return_value = [("HelloWorldFunction", False)]
        patched_confirm.side_effect = [True, False, True, True, ""]
        patched_manage_stack.return_value = "managed_s3_stack"
        self.gc.guided_prompts(parameter_override_keys=None)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(
                f"\t{self.gc.start_bold}HelloWorldFunction may not have authorization defined, Is this okay?{self.gc.end_bold}",
                default=False,
            ),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
            call(
                f"\t{self.gc.start_bold}SAM configuration file{self.gc.end_bold}",
                default="samconfig.toml",
                type=click.STRING,
            ),
            call(
                f"\t{self.gc.start_bold}SAM configuration environment{self.gc.end_bold}",
                default="default",
                type=click.STRING,
            ),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    def test_guided_prompts_check_parameter_from_template(
        self, patched_get_template_data, patchedauth_per_resource, patched_manage_stack, patched_confirm, patched_prompt
    ):
        # Series of inputs to confirmations so that full range of questions are asked.
        patchedauth_per_resource.return_value = [("HelloWorldFunction", False)]
        patched_confirm.side_effect = [True, False, True, False, ""]
        patched_manage_stack.return_value = "managed_s3_stack"
        parameter_override_from_template = {"MyTestKey": {"Default": "MyTemplateDefaultVal"}}
        self.gc.parameter_overrides_from_cmdline = {}
        self.gc.guided_prompts(parameter_override_keys=parameter_override_from_template)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(
                f"\t{self.gc.start_bold}HelloWorldFunction may not have authorization defined, Is this okay?{self.gc.end_bold}",
                default=False,
            ),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(
                f"\t{self.gc.start_bold}Parameter MyTestKey{self.gc.end_bold}",
                default="MyTemplateDefaultVal",
                type=click.STRING,
            ),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    def test_guided_prompts_check_parameter_from_cmd_or_config(
        self, patched_get_template_data, patchedauth_per_resource, patched_manage_stack, patched_confirm, patched_prompt
    ):
        # Series of inputs to confirmations so that full range of questions are asked.
        patchedauth_per_resource.return_value = [("HelloWorldFunction", False)]
        patched_confirm.side_effect = [True, False, True, False, ""]
        patched_manage_stack.return_value = "managed_s3_stack"
        parameter_override_from_template = {"MyTestKey": {"Default": "MyTemplateDefaultVal"}}
        self.gc.parameter_overrides_from_cmdline = {"MyTestKey": "OverridedValFromCmdLine", "NotUsedKey": "NotUsedVal"}
        self.gc.guided_prompts(parameter_override_keys=parameter_override_from_template)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(
                f"\t{self.gc.start_bold}HelloWorldFunction may not have authorization defined, Is this okay?{self.gc.end_bold}",
                default=False,
            ),
            call(f"\t{self.gc.start_bold}Save arguments to configuration file{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(
                f"\t{self.gc.start_bold}Parameter MyTestKey{self.gc.end_bold}",
                default="OverridedValFromCmdLine",
                type=click.STRING,
            ),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

@parameterized.expand(
        [
            param(({"MyFunction1"}, {})),
            param(({"MyFunction1", "MyFunction2"}, {})),
            param(({"MyFunction1"}, {"MyLayer1": {"MyFunction1"}})),
            param(({"MyFunction1"}, {"MyLayer1": {"MyFunction1"}, "MyLayer2": {"MyFunction1"}})),
        ]
    )
    @patch("samcli.commands.deploy.guided_context.prompt")
    @patch("samcli.commands.deploy.guided_context.confirm")
    @patch("samcli.commands.deploy.code_signer_utils.prompt")
    @patch("samcli.commands.deploy.guided_context.manage_stack")
    @patch("samcli.commands.deploy.guided_context.auth_per_resource")
    @patch("samcli.commands.deploy.guided_context.get_template_data")
    @patch("samcli.commands.deploy.guided_context.signer_config_per_function")
    def test_guided_prompts_with_code_signing(
        self,
        given_code_signing_configs,
        patched_signer_config_per_function,
        patched_get_template_data,
        patchedauth_per_resource,
        patched_manage_stack,
        patched_code_signer_prompt,
        patched_confirm,
        patched_prompt,
    ):
        patched_signer_config_per_function.return_value = given_code_signing_configs
        # Series of inputs to confirmations so that full range of questions are asked.
        patched_confirm.side_effect = [True, False, True, "", True]
        self.gc.guided_prompts(parameter_override_keys=None)
        # Now to check for all the defaults on confirmations.
        expected_confirmation_calls = [
            call(f"\t{self.gc.start_bold}Confirm changes before deploy{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Allow SAM CLI IAM role creation{self.gc.end_bold}", default=True),
            call(f"\t{self.gc.start_bold}Do you want to sign your code?{self.gc.end_bold}", default=True,),
            call(f"\t{self.gc.start_bold}Save arguments to samconfig.toml{self.gc.end_bold}", default=True),
        ]
        self.assertEqual(expected_confirmation_calls, patched_confirm.call_args_list)

        # Now to check for all the defaults on prompts.
        expected_prompt_calls = [
            call(f"\t{self.gc.start_bold}Stack Name{self.gc.end_bold}", default="test", type=click.STRING),
            call(f"\t{self.gc.start_bold}AWS Region{self.gc.end_bold}", default="region", type=click.STRING),
            call(f"\t{self.gc.start_bold}Capabilities{self.gc.end_bold}", default=["CAPABILITY_IAM"], type=ANY),
        ]
        self.assertEqual(expected_prompt_calls, patched_prompt.call_args_list)

        # we are going to expect prompts for functions and layers for each one of them,
        # so multiply the number of prompt calls
        number_of_functions = len(given_code_signing_configs[0])
        number_of_layers = len(given_code_signing_configs[1])
        expected_code_sign_calls = [
            call(f"\t{self.gc.start_bold}Signing Profile Name{self.gc.end_bold}", default=None, type=click.STRING),
            call(
                f"\t{self.gc.start_bold}Signing Profile Owner Account ID (optional){self.gc.end_bold}",
                default="",
                type=click.STRING,
                show_default=False,
            ),
        ]
        expected_code_sign_calls = expected_code_sign_calls * (number_of_functions + number_of_layers)
        self.assertEqual(expected_code_sign_calls, patched_code_signer_prompt.call_args_list)
