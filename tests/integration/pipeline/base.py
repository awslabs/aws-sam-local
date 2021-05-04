import os
import shutil
from pathlib import Path
from typing import List, Optional, Set, Tuple
from unittest import TestCase
from unittest.mock import Mock

import boto3

from samcli.lib.pipeline.bootstrap.stage import Stage
from tests.testing_utils import run_command_with_input, CommandResult


class PipelineBase(TestCase):
    def base_command(self):
        command = "sam"
        if os.getenv("SAM_CLI_DEV"):
            command = "samdev"

        return command

    def run_command_with_inputs(self, command_list: List[str], inputs: List[str]) -> CommandResult:
        return run_command_with_input(command_list, ("\n".join(inputs) + "\n").encode())


class InitIntegBase(PipelineBase):
    generated_files: List[Path] = []

    @classmethod
    def setUpClass(cls) -> None:
        # we need to compare the whole generated template, which is
        # larger than normal diff size limit
        cls.maxDiff = None

    def setUp(self) -> None:
        super().setUp()
        self.generated_files = []

    def tearDown(self) -> None:
        for generated_file in self.generated_files:
            if generated_file.is_dir():
                shutil.rmtree(generated_file, ignore_errors=True)
            elif generated_file.exists():
                generated_file.unlink()
        super().tearDown()

    def get_init_command_list(
        self,
    ):
        command_list = [self.base_command(), "pipeline", "init"]
        return command_list


class BootstrapIntegBase(PipelineBase):
    stack_names: List[str]

    @classmethod
    def setUpClass(cls):
        cls.cf_client = boto3.client("cloudformation")

    def setUp(self):
        self.stack_names = []
        super().setUp()

    def tearDown(self):
        for stack_name in self.stack_names:
            self.cf_client.delete_stack(StackName=stack_name)
        shutil.rmtree(os.path.join(os.getcwd(), ".aws-sam", "pipeline"), ignore_errors=True)
        super().tearDown()

    def get_bootstrap_command_list(
        self,
        no_interactive: bool = False,
        stage_name: Optional[str] = None,
        pipeline_user: Optional[str] = None,
        pipeline_execution_role: Optional[str] = None,
        cloudformation_execution_role: Optional[str] = None,
        artifacts_bucket: Optional[str] = None,
        create_ecr_repo: bool = False,
        ecr_repo: Optional[str] = None,
        pipeline_ip_range: Optional[str] = None,
        no_confirm_changeset: bool = False,
    ):
        command_list = [self.base_command(), "pipeline", "bootstrap"]

        if no_interactive:
            command_list += ["--no-interactive"]
        if stage_name:
            command_list += ["--stage-name", stage_name]
        if pipeline_user:
            command_list += ["--pipeline-user", pipeline_user]
        if pipeline_execution_role:
            command_list += ["--pipeline-execution-role", pipeline_execution_role]
        if cloudformation_execution_role:
            command_list += ["--cloudformation-execution-role", cloudformation_execution_role]
        if artifacts_bucket:
            command_list += ["--artifacts-bucket", artifacts_bucket]
        if create_ecr_repo:
            command_list += ["--create-ecr-repo"]
        if ecr_repo:
            command_list += ["--ecr-repo", ecr_repo]
        if pipeline_ip_range:
            command_list += ["--pipeline-ip-range", pipeline_ip_range]
        if no_confirm_changeset:
            command_list += ["--no-confirm-changeset"]

        return command_list

    def _extract_created_resource_logical_ids(self, stack_name: str) -> Set[str]:
        response = self.cf_client.describe_stack_resources(StackName=stack_name)
        return {resource["LogicalResourceId"] for resource in response["StackResources"]}

    def _get_stage_and_stack_name(self, suffix: str = "") -> Tuple[str, str]:
        # Method expects method name which can be a full path. Eg: test.integration.test_bootstrap_command.method_name
        method_name = self.id().split(".")[-1]
        stage_name = method_name.replace("_", "-") + suffix

        mock_stage = Mock()
        mock_stage.name = stage_name
        stack_name = Stage._get_stack_name(mock_stage)

        return stage_name, stack_name
