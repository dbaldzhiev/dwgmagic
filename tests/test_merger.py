import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import subprocess as sp
import merger
import logger as lg
import script_generator as sg
import config as cfg

class TestMerger(unittest.TestCase):

    @patch('subprocess.Popen')
    def test_run_command(self, mock_popen):
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("output", "error")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        output, err = merger.run_command(["echo", "test"])
        self.assertEqual(output, "output")
        self.assertEqual(err, "error")
        mock_popen.assert_called_with(["echo", "test"], stdout=sp.PIPE, shell=True, encoding='utf-16-le', errors='replace')

    @patch('merger.console.print')
    @patch('config.verbose', True)
    def test_log_and_print(self, mock_print):
        mock_log = MagicMock()
        merger.log_and_print("Test message", mock_log, "bold yellow")
        mock_log.debug.assert_called_with("Test message")
        mock_print.assert_called_with("Test message", style="bold yellow")

    @patch('merger.sg.generate_view_script')
    @patch('merger.lg.setup_logger')
    @patch('merger.run_command')
    def test_view_worker(self, mock_run_command, mock_setup_logger, mock_generate_view_script):
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger
        mock_run_command.return_value = ("output", None)
        
        merger.view_worker("test.dwg", "/path/to/acc", "/path/to/logs")
        mock_generate_view_script.assert_called_with("test", "TEST.scr", log_dir="/path/to/logs")
        mock_setup_logger.assert_called_with("TEST", log_dir="/path/to/logs")
        mock_run_command.assert_called()
        
    @patch('merger.sg.generate_sheet_script')
    @patch('merger.lg.setup_logger')
    @patch('merger.run_command')
    @patch('os.remove')
    def test_sheet_worker(self, mock_remove, mock_run_command, mock_setup_logger, mock_generate_sheet_script):
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger
        mock_run_command.return_value = ("output", None)
        
        merger.sheet_worker("test.dwg", "/path/to/acc", "/path/to/logs", ["test-View-1.dwg"])
        mock_generate_sheet_script.assert_called_with("test", ["test-View-1.dwg"], "TEST_SHEET.scr", log_dir="/path/to/logs")
        mock_setup_logger.assert_called_with("SHEET_test", log_dir="/path/to/logs")
        mock_run_command.assert_called()
        mock_remove.assert_called_with(f"{os.getcwd()}/derevitized/test.dwg")

    @patch('merger.os.listdir')
    @patch('merger.checks.acc_version')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_setup_environment(self, mock_makedirs, mock_open, mock_acc_version, mock_listdir):
        mock_listdir.return_value = ["file1.dwg", "file2-View-1.dwg"]
        mock_acc_version.return_value = "/path/to/acc"
        
        with patch('merger.Project.generate_scripts'), \
             patch('merger.Project.process_views'), \
             patch('merger.Project.process_sheets'), \
             patch('merger.Project.merge_results'):
            project = merger.Project()
            project.setup_environment()
            self.assertEqual(project.files, ["file1.dwg", "file2-View-1.dwg"])
            self.assertEqual(project.acc_path, "/path/to/acc")
            self.assertEqual(project.sheet, ["file1.dwg"])
            self.assertEqual(project.view, ["file2-View-1.dwg"])

if __name__ == "__main__":
    unittest.main()
