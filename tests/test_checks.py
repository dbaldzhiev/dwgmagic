import unittest
from unittest.mock import patch, MagicMock
import checks as ck

class TestChecks(unittest.TestCase):

    @patch('checks.os.path.exists')
    @patch('checks.sys.exit')
    def test_acc_version(self, mock_exit, mock_exists):
        # First, simulate that one of the paths exists
        mock_exists.side_effect = lambda path: path == "/path/to/acc"
        ck.cfg.accpathv = {'ver1': '/path/to/acc', 'ver2': '/another/path'}
        result = ck.acc_version()
        self.assertEqual(result, "/path/to/acc")
        mock_exit.assert_not_called()

        # Now simulate that none of the paths exist
        mock_exists.side_effect = lambda path: False
        ck.cfg.accpathv = {'ver1': '/nonexistent/path1', 'ver2': '/nonexistent/path2'}
        ck.acc_version()
        mock_exit.assert_called_with('Cannot find accoreconsole.exe')

    @patch('checks.setup_logger')
    @patch('checks.acc_version')
    @patch('subprocess.Popen')
    @patch('sys.exit')
    def test_checks(self, mock_exit, mock_popen, mock_acc_version, mock_setup_logger):
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger
        mock_acc_version.return_value = "/path/to/acc"
        process_mock = MagicMock()
        process_mock.communicate.return_value = ("output", None)
        mock_popen.return_value = process_mock

        # First run, no error in output
        ck.checks(log_dir="logs")
        mock_setup_logger.assert_called_with("CHECKS", log_dir="logs")
        mock_logger.info.assert_any_call("ACCORECONSOLE PATH: %s", "/path/to/acc")
        mock_popen.assert_called()
        mock_exit.assert_not_called()

        # Second run, error in output
        process_mock.communicate.return_value = ("Unable to load C:\\dwgmagic\\tectonica.dll assembly.", None)
        try:
            ck.checks(log_dir="logs")
        except SystemExit:
            pass  # Expected exit

        mock_exit.assert_called_with("TRUSTED FOLDER IS NOT SET UP")

if __name__ == "__main__":
    unittest.main()
