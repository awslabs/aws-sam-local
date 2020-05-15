import re
import time
import json
import logging
from subprocess import Popen, PIPE, TimeoutExpired
from parameterized import parameterized

from unittest import skipIf

from samcli.commands.publish.command import SEMANTIC_VERSION
from .publish_app_integ_base import PublishAppIntegBase
from tests.testing_utils import RUNNING_ON_CI, RUNNING_TEST_FOR_MASTER_ON_CI, RUN_BY_CANARY
from tests.testing_utils import run_command

# Publish tests require credentials and CI/CD will only add credentials to the env if the PR is from the same repo.
# This is to restrict publish tests to run outside of CI/CD, when the branch is not master and tests are not run by Canary.
SKIP_PUBLISH_TESTS = RUNNING_ON_CI and RUNNING_TEST_FOR_MASTER_ON_CI and not RUN_BY_CANARY
TIMEOUT = 300

LOG = logging.getLogger(__name__)


@skipIf(SKIP_PUBLISH_TESTS, "Skip publish tests in CI/CD only")
class TestPublishExistingApp(PublishAppIntegBase):
    def setUp(self):
        super(TestPublishExistingApp, self).setUp()
        # Create application for each test
        app_metadata_text = self.temp_dir.joinpath("metadata_create_app.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        app_metadata["TemplateBody"] = self.temp_dir.joinpath("template_create_app.yaml").read_text()
        response = self.sar_client.create_application(**app_metadata)
        self.application_id = response["ApplicationId"]

        # Sleep for a little bit to make server happy
        time.sleep(2)

    def tearDown(self):
        super(TestPublishExistingApp, self).tearDown()
        # Delete application for each test
        # self.sar_client.delete_application(ApplicationId=self.application_id)

    def test_update_application(self):
        template_path = self.temp_dir.joinpath("template_update_app.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        result = run_command(command_list)
        expected_msg = 'The following metadata of application "{}" has been updated:'.format(self.application_id)
        self.assertIn(expected_msg, result.stdout.decode("utf-8"))

        app_metadata_text = self.temp_dir.joinpath("metadata_update_app.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        self.assert_metadata_details(app_metadata, result.stdout.decode("utf-8"))

    def test_create_application_version(self):
        template_path = self.temp_dir.joinpath("template_create_app_version.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)
        result = run_command(command_list)

        expected_msg = 'The following metadata of application "{}" has been updated:'.format(self.application_id)
        self.assertIn(expected_msg, result.stdout.decode("utf-8"))

        app_metadata_text = self.temp_dir.joinpath("metadata_create_app_version.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        self.assert_metadata_details(app_metadata, result.stdout.decode("utf-8"))

    def test_create_application_version_with_semantic_version_option(self):
        template_path = self.temp_dir.joinpath("template_create_app_version.yaml")
        command_list = self.get_command_list(
            template_path=template_path, region=self.region_name, semantic_version="0.1.0"
        )
        result = run_command(command_list)
        expected_msg = 'The following metadata of application "{}" has been updated:'.format(self.application_id)
        self.assertIn(expected_msg, result.stdout.decode("utf-8"))

        app_metadata_text = self.temp_dir.joinpath("metadata_create_app_version.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        app_metadata[SEMANTIC_VERSION] = "0.1.0"
        self.assert_metadata_details(app_metadata, result.stdout.decode("utf-8"))

    @parameterized.expand(
        [
            ("template_create_app_with_readme_bodies.yaml", "metadata_create_app_with_readme_bodies.json"),
        ]
    )
    def test_create_application_version_with_read_and_license_bodies(self, template_filename, expected_template_filename):
        template_path = self.temp_dir.joinpath(template_filename)
        command_list = self.get_command_list(
            template_path=template_path, region=self.region_name, semantic_version="0.1.0"
        )
        result = run_command(command_list)
        expected_msg = 'The following metadata of application "{}" has been updated:'.format(self.application_id)
        result_msg = result.stdout.decode("utf-8")
        self.assertIn(expected_msg, result_msg)

        app_metadata_text = self.temp_dir.joinpath(expected_template_filename).read_text()
        app_metadata = json.loads(app_metadata_text)
        app_metadata[SEMANTIC_VERSION] = "0.1.0"
        self.assert_metadata_details(app_metadata, result_msg)


@skipIf(SKIP_PUBLISH_TESTS, "Skip publish tests in CI/CD only")
class TestPublishNewApp(PublishAppIntegBase):
    def setUp(self):
        super(TestPublishNewApp, self).setUp()
        self.application_id = None
        # Sleep for a little bit to make server happy
        time.sleep(2)

    def tearDown(self):
        super(TestPublishNewApp, self).tearDown()
        # Delete application if exists
        if self.application_id:
            self.sar_client.delete_application(ApplicationId=self.application_id)

    def test_create_application(self):
        template_path = self.temp_dir.joinpath("template_create_app.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        result = run_command(command_list)
        expected_msg = "Created new application with the following metadata:"
        self.assertIn(expected_msg, result.stdout.decode("utf-8"))

        app_metadata_text = self.temp_dir.joinpath("metadata_create_app.json").read_text()
        app_metadata = json.loads(app_metadata_text)
        self.assert_metadata_details(app_metadata, result.stdout.decode("utf-8"))

        # Get console link application id from stdout
        pattern = r"arn:[\w\-]+:serverlessrepo:[\w\-]+:[0-9]+:applications\~[\S]+"
        match = re.search(pattern, result.stdout.decode("utf-8"))
        self.application_id = match.group().replace("~", "/")

    def test_publish_not_packaged_template(self):
        template_path = self.temp_dir.joinpath("template_not_packaged.yaml")
        command_list = self.get_command_list(template_path=template_path, region=self.region_name)

        process = Popen(command_list, stderr=PIPE)
        try:
            _, stderr = process.communicate(timeout=TIMEOUT)
        except TimeoutExpired:
            process.kill()
            raise
        process_stderr = stderr.strip()

        expected_msg = "Please make sure that you have uploaded application artifacts to S3"
        self.assertIn(expected_msg, process_stderr.decode("utf-8"))

    def test_create_application_infer_region_from_env(self):
        template_path = self.temp_dir.joinpath("template_create_app.yaml")
        command_list = self.get_command_list(template_path=template_path)

        result = run_command(command_list)

        expected_msg = "Created new application with the following metadata:"
        self.assertIn(expected_msg, result.stdout.decode("utf-8"))

        # Get console link application id from stdout
        pattern = r"arn:[\w\-]+:serverlessrepo:[\w\-]+:[0-9]+:applications\~[\S]+"
        match = re.search(pattern, result.stdout.decode("utf-8"))
        self.application_id = match.group().replace("~", "/")
        self.assertIn(self.region_name, self.application_id)
