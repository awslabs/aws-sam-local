from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch, call, ANY

from samcli.cli.global_config import GlobalConfig
from samcli.lib.utils.version_checker import (
    check_newer_version,
    is_last_check_older_then_week,
    update_last_check_time,
    compare_current_version,
    AWS_SAM_CLI_INSTALL_DOCS,
    AWS_SAM_CLI_PYPI_ENDPOINT,
    PYPI_CALL_TIMEOUT_IN_SECONDS,
)


@check_newer_version
def real_fn(a, b=None):
    return f"{a} {b}"


class TestVersionChecker(TestCase):
    def test_must_decorate_functions(self):
        actual = real_fn("Hello", "World")
        self.assertEqual(actual, "Hello World")

    @patch("samcli.lib.utils.version_checker.is_last_check_older_then_week")
    @patch("samcli.lib.utils.version_checker.compare_current_version")
    @patch("samcli.lib.utils.version_checker.update_last_check_time")
    def test_must_call_compare_current_version_if_newer_version_is_available(
        self, mock_update_last_check, mock_compare_current_version, mock_is_last_check_older
    ):
        mock_is_last_check_older.return_value = True
        actual = real_fn("Hello", "World")

        self.assertEqual(actual, "Hello World")
        mock_is_last_check_older.assert_called_once()
        mock_compare_current_version.assert_called_once()
        mock_update_last_check.assert_called_once()

    @patch("samcli.lib.utils.version_checker.is_last_check_older_then_week")
    @patch("samcli.lib.utils.version_checker.compare_current_version")
    @patch("samcli.lib.utils.version_checker.update_last_check_time")
    def test_must_not_call_compare_current_version_if_no_newer_version_is_available(
        self, mock_update_last_check, mock_compare_current_version, mock_is_last_check_older
    ):
        mock_is_last_check_older.return_value = False
        actual = real_fn("Hello", "World")

        self.assertEqual(actual, "Hello World")
        mock_is_last_check_older.assert_called_once()

        mock_compare_current_version.assert_not_called()
        mock_update_last_check.assert_not_called()

    @patch("samcli.lib.utils.version_checker.get")
    @patch("samcli.cli.global_config.GlobalConfig._get_value")
    def test_actual_function_should_return_on_exception(self, get_value_mock, get_mock):
        get_value_mock.return_value = None
        get_mock.side_effect = Exception()
        actual = real_fn("Hello", "World")
        self.assertEqual(actual, "Hello World")

    @patch("samcli.lib.utils.version_checker.get")
    @patch("samcli.lib.utils.version_checker.LOG")
    @patch("samcli.lib.utils.version_checker.installed_version", "1.9.0")
    def test_compare_invalid_response(self, mock_log, get_mock):
        get_mock.return_value.json.return_value = {}
        compare_current_version()

        get_mock.assert_has_calls([call(AWS_SAM_CLI_PYPI_ENDPOINT, timeout=PYPI_CALL_TIMEOUT_IN_SECONDS)])

        mock_log.assert_has_calls(
            [
                call.debug("Installed version %s, current version %s", "1.9.0", None),
            ]
        )

    @patch("samcli.lib.utils.version_checker.get")
    @patch("samcli.lib.utils.version_checker.LOG")
    @patch("samcli.lib.utils.version_checker.installed_version", "1.9.0")
    def test_compare_current_versions_same(self, mock_log, get_mock):
        get_mock.return_value.json.return_value = {"info": {"version": "1.9.0"}}
        compare_current_version()

        get_mock.assert_has_calls([call(AWS_SAM_CLI_PYPI_ENDPOINT, timeout=PYPI_CALL_TIMEOUT_IN_SECONDS)])

        mock_log.assert_has_calls(
            [
                call.debug("Installed version %s, current version %s", "1.9.0", "1.9.0"),
            ]
        )

    @patch("samcli.lib.utils.version_checker.get")
    @patch("samcli.lib.utils.version_checker.click")
    @patch("samcli.lib.utils.version_checker.installed_version", "1.9.0")
    def test_compare_current_versions_different(self, mock_click, get_mock):
        get_mock.return_value.json.return_value = {"info": {"version": "1.10.0"}}
        compare_current_version()

        get_mock.assert_has_calls([call(AWS_SAM_CLI_PYPI_ENDPOINT, timeout=PYPI_CALL_TIMEOUT_IN_SECONDS)])

        mock_click.assert_has_calls(
            [
                call.secho("\nSAM CLI update available (1.10.0); (1.9.0 installed)", fg="green"),
                call.echo(f"To download: {AWS_SAM_CLI_INSTALL_DOCS}"),
            ]
        )

    @patch("samcli.cli.global_config.GlobalConfig._set_value")
    @patch("samcli.cli.global_config.GlobalConfig._get_value")
    def test_update_last_check_time(self, mock_gc_get_value, mock_gc_set_value):
        mock_gc_get_value.return_value = None
        global_config = GlobalConfig()
        self.assertIsNone(global_config.last_version_check)

        update_last_check_time(global_config)
        self.assertIsNotNone(global_config.last_version_check)

        mock_gc_set_value.assert_has_calls([call("lastVersionCheck", ANY)])

    @patch("samcli.cli.global_config.GlobalConfig._set_value")
    @patch("samcli.cli.global_config.GlobalConfig._get_value")
    def test_update_last_check_time_should_return_when_exception_is_raised(self, mock_gc_get_value, mock_gc_set_value):
        mock_gc_set_value.side_effect = Exception()
        global_config = GlobalConfig()
        update_last_check_time(global_config)

    def test_update_last_check_time_should_return_when_global_config_is_none(self):
        update_last_check_time(None)

    def test_last_check_time_none_should_return_true(self):
        self.assertTrue(is_last_check_older_then_week(None))

    def test_last_check_time_week_older_should_return_true(self):
        eight_days_ago = datetime.utcnow() - timedelta(days=8)
        self.assertTrue(is_last_check_older_then_week(eight_days_ago))

    def test_last_check_time_week_earlier_should_return_false(self):
        eight_days_ago = datetime.utcnow() - timedelta(days=6)
        self.assertFalse(is_last_check_older_then_week(eight_days_ago.timestamp()))
