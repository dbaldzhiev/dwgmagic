import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import script_generator as sg
from unittest import mock

class TestScriptGenerator(unittest.TestCase):

    @patch('script_generator.setup_logger')
    @patch('script_generator.env.get_template')
    def test_generate_script(self, mock_get_template, mock_setup_logger):
        mock_template = MagicMock()
        mock_get_template.return_value = mock_template
        mock_template.render.return_value = "rendered content"
        logger = MagicMock()
        mock_setup_logger.return_value = logger

        with patch('builtins.open', mock_open()) as mocked_file:
            sg.generate_script('template.tmpl', '/path/to/output', logger, context_key='value')
            mocked_file.assert_called_with('/path/to/output', 'w', encoding='utf-8')
            mocked_file().write.assert_called_with('rendered content')
            logger.info.assert_called_with("Generated script %s", '/path/to/output')

    @patch('script_generator.generate_script')
    def test_generate_project_script(self, mock_generate_script):
        sg.generate_project_script(['sheet1', 'sheet2'], True, ['sheet'])
        mock_generate_script.assert_called_with(
            './templates/project_script_template.tmpl', './scripts/DWGMAGIC.scr', 
            mock.ANY,
            sheetNamesList=['sheet1', 'sheet2'],
            tectonica_path=sg.cfg.DMM_PATH,
            project_name=os.path.basename(os.getcwd()),
            xrefXplodeToggle=True,
            sheets=['sheet']
        )

    @patch('script_generator.generate_script')
    def test_generate_manual_master_merge_script(self, mock_generate_script):
        sg.generate_manual_master_merge_script(True, ['sheet'])
        mock_generate_script.assert_called_with(
            './templates/mmm_script_template.tmpl', './scripts/MMM.scr', 
            mock.ANY,
            tectonica_path=sg.cfg.DMM_PATH,
            xrefXplodeToggle=True,
            sheets=['sheet'],
            project_name=os.path.basename(os.getcwd())
        )

    @patch('script_generator.generate_script')
    def test_generate_manual_master_merge_bat(self, mock_generate_script):
        sg.generate_manual_master_merge_bat('/path/to/acc')
        mock_generate_script.assert_called_with(
            './templates/manual_merge_bat_template.tmpl', './MANUALMERGE.bat', 
            mock.ANY,
            acc='/path/to/acc',
            project_name=os.path.basename(os.getcwd())
        )

if __name__ == "__main__":
    unittest.main()
