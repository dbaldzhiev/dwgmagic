import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
from datetime import datetime
import miscutil as mu

class TestMiscUtil(unittest.TestCase):

    @patch('os.listdir')
    def test_get_dwg_files_in_directory(self, mock_listdir):
        mock_listdir.return_value = ["file1.dwg", "file2.dwg", "file3.txt"]
        dwg_files = mu.get_dwg_files_in_directory("/some/path")
        self.assertEqual(dwg_files, ["file1.dwg", "file2.dwg"])
        
        mock_listdir.return_value = []
        with self.assertRaises(SystemExit):
            mu.get_dwg_files_in_directory("/some/path")

    @patch('os.path.isfile')
    @patch('os.remove')
    def test_safe_remove_file(self, mock_remove, mock_isfile):
        mock_isfile.return_value = True
        mu.safe_remove("/some/path/file.dwg")
        mock_remove.assert_called_with("/some/path/file.dwg")

    @patch('shutil.rmtree')
    @patch('os.path.isdir')
    def test_safe_remove_directory(self, mock_isdir, mock_rmtree):
        mock_isdir.return_value = True
        mu.safe_remove("/some/path/directory")
        mock_rmtree.assert_called_with("/some/path/directory")

    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_create_directory(self, mock_mkdir, mock_exists):
        mock_exists.return_value = False
        mu.create_directory("/some/path/directory")
        mock_mkdir.assert_called_with("/some/path/directory")

    @patch('os.path.exists')
    @patch('os.rename')
    def test_cleanup_old_logs(self, mock_rename, mock_exists):
        mock_exists.return_value = True
        with patch('miscutil.create_directory') as mock_create_directory:
            mu.cleanup_old_logs("/some/path/logs")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            mock_rename.assert_called_with("/some/path/logs", f"/some/path/logs_backup_{timestamp}")
            mock_create_directory.assert_called_with("/some/path/logs")

    @patch('shutil.copy')
    @patch('os.remove')
    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_preprocess(self, mock_mkdir, mock_exists, mock_remove, mock_copy):
        mock_exists.return_value = False
        with patch('miscutil.get_dwg_files_in_directory') as mock_get_dwg_files, \
             patch('miscutil.remove_previous_preprocess') as mock_remove_previous, \
             patch('miscutil.setup_logger') as mock_setup_logger:
            mock_get_dwg_files.return_valu
