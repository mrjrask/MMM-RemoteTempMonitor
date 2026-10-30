"""Install/update regression tests using isolated files and mocked systemd."""
import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'remote-service/Pi/install-full.sh'
loader = importlib.machinery.SourceFileLoader('installer', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patcher = patch.multiple(module, INSTALL_DIR=self.root/'opt', SYSTEMD_DIR=self.root/'units', ENV_DIR=self.root/'env')
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.user = patch.object(module.pwd, 'getpwnam')
        self.user.start(); self.addCleanup(self.user.stop)

    def test_install_copies_correct_files_and_account(self):
        with patch.dict(module.os.environ, {'SUDO_USER': 'mirror'}):
            services, plan = module.build_plan()
        with patch.object(module, 'run'), patch.object(module.time, 'sleep'), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 3)):
            module.apply_plan(services, plan)
        self.assertEqual((module.INSTALL_DIR/'temp_broadcaster.py').read_bytes(), (SOURCE.parent/'temp_broadcaster.py').read_bytes())
        self.assertTrue((module.INSTALL_DIR/'status/broadcaster_common.py').exists())
        self.assertIn('User=mirror', (module.SYSTEMD_DIR/'temp-monitor.service').read_text())
        self.assertEqual((module.ENV_DIR/'temp-monitor').stat().st_mode & 0o777, 0o600)

    def test_update_preserves_environment_and_existing_account(self):
        module.SYSTEMD_DIR.mkdir()
        (module.SYSTEMD_DIR/'temp-monitor.service').write_text('[Service]\nUser=existing\n')
        module.ENV_DIR.mkdir()
        (module.ENV_DIR/'temp-monitor').write_text('custom secret')
        services, plan = module.build_plan(update=True)
        self.assertEqual(services, ['temp-monitor'])
        self.assertNotIn(module.ENV_DIR/'temp-monitor', [entry[0] for entry in plan])
        unit = next(content for path, content, _ in plan if path.name == 'temp-monitor.service')
        self.assertIn(b'User=existing', unit)

    def test_failed_restart_rolls_back(self):
        target = self.root/'script.py'; target.write_bytes(b'old')
        new = self.root/'new.py'
        def run(command):
            if command[:2] == ['systemctl', 'restart']:
                raise subprocess.CalledProcessError(1, command)
        with patch.object(module, 'run', side_effect=run), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaises(subprocess.CalledProcessError):
                module.apply_plan(['temp-monitor'], [(target, b'new', 0o755), (new, b'new file', 0o644)])
        self.assertEqual(target.read_bytes(), b'old')
        self.assertFalse(new.exists())

    def test_crash_after_restart_rolls_back(self):
        target = self.root/'script.py'; target.write_bytes(b'old')
        def run(command):
            if command[:2] == ['systemctl', 'is-active']:
                raise subprocess.CalledProcessError(3, command)
        with patch.object(module, 'run', side_effect=run), patch.object(module.time, 'sleep'), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaises(subprocess.CalledProcessError):
                module.apply_plan(['temp-monitor'], [(target, b'new', 0o755)])
        self.assertEqual(target.read_bytes(), b'old')

    def test_backup_retention(self):
        target = self.root/'script.py'; target.write_bytes(b'old')
        for index in range(5):
            (self.root/f'script.py.backup.old{index}').write_text('backup')
        with patch.object(module, 'run'), patch.object(module.time, 'sleep'), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
            module.apply_plan(['temp-monitor'], [(target, b'new', 0o755)])
        self.assertEqual(len(list(self.root.glob('script.py.backup.*'))), 3)

    def test_missing_source_fails_before_systemd(self):
        with patch.object(module, 'SOURCE_DIR', self.root), patch.object(module.subprocess, 'run') as run:
            with self.assertRaises(FileNotFoundError): module.build_plan()
            run.assert_not_called()
