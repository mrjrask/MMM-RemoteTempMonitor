"""Git-status parsing regression tests; no global subprocess mutation."""
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'remote-service/Pi/status-broadcaster.py'
spec = importlib.util.spec_from_file_location('status_git', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GitTests(unittest.TestCase):
    def test_clean_and_dirty_status(self):
        item = module.StatusBroadcaster.__new__(module.StatusBroadcaster)
        for output, expected in [('', False), (' M notes.txt\n', True), ('?? new.txt\n', True), ('A  new.txt\n', True), (' D old.txt\n', True), ('R  old -> new\n', True), ('UU conflict.txt\n', True)]:
            with self.subTest(output=output), patch.object(module.Path, 'exists', return_value=True), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output, '')):
                self.assertEqual(item._check_desk_display_git_status(), expected)

    def test_missing_repo(self):
        item = module.StatusBroadcaster.__new__(module.StatusBroadcaster)
        with patch.object(module.Path, 'exists', return_value=False), patch.object(module.subprocess, 'run') as run:
            self.assertFalse(item._check_desk_display_git_status())
            run.assert_not_called()

    def test_repo_override_and_git_failure(self):
        item = module.StatusBroadcaster.__new__(module.StatusBroadcaster)
        with patch.dict(os.environ, {'STATUS_BROADCAST_REPO': '/custom/repo'}), patch.object(module.Path, 'exists', return_value=True), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'error')) as run:
            self.assertFalse(item._check_desk_display_git_status())
            self.assertIn('/custom/repo', run.call_args.args[0])
