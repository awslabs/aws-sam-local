from unittest import TestCase
from unittest.mock import patch

from samcli.commands.pipeline.bootstrap.guided_context import GuidedContext

ANY_STAGE_NAME = "ANY_STAGE_NAME"
ANY_PIPELINE_USER_ARN = "ANY_PIPELINE_USER_ARN"
ANY_PIPELINE_EXECUTION_ROLE_ARN = "ANY_PIPELINE_EXECUTION_ROLE_ARN"
ANY_CLOUDFORMATION_EXECUTION_ROLE_ARN = "ANY_CLOUDFORMATION_EXECUTION_ROLE_ARN"
ANY_ARTIFACTS_BUCKET_ARN = "ANY_ARTIFACTS_BUCKET_ARN"
ANY_ECR_REPO_ARN = "ANY_ECR_REPO_ARN"
ANY_ARN = "ANY_ARN"
ANY_PIPELINE_IP_RANGE = "111.222.333.0/24"


class TestGuidedContext(TestCase):
    @patch("samcli.commands.pipeline.bootstrap.guided_context.click")
    def test_guided_context_will_not_prompt_for_fields_that_are_already_provided(self, click_mock):
        gc: GuidedContext = GuidedContext(
            stage_name=ANY_STAGE_NAME,
            pipeline_user_arn=ANY_PIPELINE_USER_ARN,
            pipeline_execution_role_arn=ANY_PIPELINE_EXECUTION_ROLE_ARN,
            cloudformation_execution_role_arn=ANY_CLOUDFORMATION_EXECUTION_ROLE_ARN,
            artifacts_bucket_arn=ANY_ARTIFACTS_BUCKET_ARN,
            create_ecr_repo=True,
            ecr_repo_arn=ANY_ECR_REPO_ARN,
            pipeline_ip_range=ANY_PIPELINE_IP_RANGE,
        )
        gc.run()
        click_mock.prompt.assert_not_called()

    @patch("samcli.commands.pipeline.bootstrap.guided_context.click")
    def test_guided_context_will_prompt_for_fields_that_are_not_provided(self, click_mock):
        gc: GuidedContext = GuidedContext(
            ecr_repo_arn=ANY_ECR_REPO_ARN  # Exclude ECR repo, it has its own detailed test below
        )
        gc.run()
        self.assertTrue(self.did_prompt_text_like("Stage Name", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("Pipeline user", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("Pipeline execution role", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("CloudFormation execution role", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("Artifacts bucket", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("Artifacts bucket", click_mock.prompt))
        self.assertTrue(self.did_prompt_text_like("Pipeline IP address range", click_mock.prompt))

    @patch("samcli.commands.pipeline.bootstrap.guided_context.click")
    def test_guided_context_will_not_prompt_for_not_provided_ecr_repo_if_no_ecr_repo_is_required(self, click_mock):
        # ECR Repo choices:
        # 1 - No, My SAM Template won't include lambda functions of Image package-type
        # 2 - Yes, I need a help creating one
        # 3 - I already have an ECR repo
        gc_without_ecr_info: GuidedContext = GuidedContext(
            stage_name=ANY_STAGE_NAME,
            pipeline_user_arn=ANY_PIPELINE_USER_ARN,
            pipeline_execution_role_arn=ANY_PIPELINE_EXECUTION_ROLE_ARN,
            cloudformation_execution_role_arn=ANY_CLOUDFORMATION_EXECUTION_ROLE_ARN,
            artifacts_bucket_arn=ANY_ARTIFACTS_BUCKET_ARN,
            pipeline_ip_range=ANY_PIPELINE_IP_RANGE,
        )

        self.assertIsNone(gc_without_ecr_info.ecr_repo_arn)

        click_mock.prompt.return_value = "1"  # the user chose to not CREATE an ECR repo
        gc_without_ecr_info.run()
        self.assertIsNone(gc_without_ecr_info.ecr_repo_arn)
        self.assertFalse(gc_without_ecr_info.create_ecr_repo)
        self.assertFalse(self.did_prompt_text_like("ECR repo", click_mock.prompt))

        click_mock.prompt.return_value = "2"  # the user chose to CREATE an ECR repo
        gc_without_ecr_info.run()
        self.assertIsNone(gc_without_ecr_info.ecr_repo_arn)
        self.assertTrue(gc_without_ecr_info.create_ecr_repo)
        self.assertFalse(self.did_prompt_text_like("ECR repo", click_mock.prompt))

        click_mock.prompt.side_effect = ["3", ANY_ECR_REPO_ARN]  # the user already has a repo
        gc_without_ecr_info.run()
        self.assertFalse(gc_without_ecr_info.create_ecr_repo)
        self.assertTrue(self.did_prompt_text_like("ECR repo", click_mock.prompt))  # we've asked about it
        self.assertEqual(gc_without_ecr_info.ecr_repo_arn, ANY_ECR_REPO_ARN)

    @staticmethod
    def did_prompt_text_like(txt, click_prompt_mock):
        txt = txt.lower()
        for kall in click_prompt_mock.call_args_list:
            args, kwargs = kall
            if args:
                text = args[0].lower()
            else:
                text = kwargs.get("text", "").lower()
            if txt in text:
                return True
        return False
