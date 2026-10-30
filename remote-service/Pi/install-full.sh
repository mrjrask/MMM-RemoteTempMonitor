#!/usr/bin/env python3
"""Install/update Pi broadcasters transactionally, preserving configuration."""
from __future__ import annotations
import argparse
import os
import pwd
import re
import shutil
import sys
import subprocess
import tempfile
import time
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent
INSTALL_DIR = Path('/opt/remote-temp-monitor')
SYSTEMD_DIR = Path('/etc/systemd/system')
ENV_DIR = Path('/etc/default')
BACKUP_KEEP = 3


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)


def atomic_write(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def service_user(unit):
    if unit.exists():
        match = re.search(r'^User=(.+)$', unit.read_text(), re.MULTILINE)
        if match:
            return match.group(1).strip()
    return os.getenv('TEMP_MONITOR_SERVICE_USER') or os.getenv('SUDO_USER') or 'pi'


def build_plan(update=False):
    if update and not (SYSTEMD_DIR / 'temp-monitor.service').exists():
        raise RuntimeError('Temperature service not installed; run install.sh first')
    services = ['temp-monitor']
    if not update or (SYSTEMD_DIR / 'status-monitor.service').exists():
        services.append('status-monitor')
    plan = []
    common = SOURCE_DIR.parent / 'broadcaster_common.py'
    compile(common.read_bytes(), str(common), 'exec')
    for service in services:
        status = service == 'status-monitor'
        script = 'status-broadcaster.py' if status else 'temp_broadcaster.py'
        destination = INSTALL_DIR / 'status' if status else INSTALL_DIR
        unit = SYSTEMD_DIR / (service + '.service')
        user = service_user(unit)
        pwd.getpwnam(user)  # Fail before changes if the selected account does not exist.
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', user):
            raise ValueError('Unsupported service account name')
        script_source = SOURCE_DIR / script
        compile(script_source.read_bytes(), str(script_source), 'exec')
        unit_text = (SOURCE_DIR / (service + '.service')).read_text()
        unit_text = re.sub(r'^User=.*$', 'User=' + user, unit_text, flags=re.MULTILINE)
        plan.extend([(destination / script, script_source.read_bytes(), 0o755),
                     (destination / common.name, common.read_bytes(), 0o644),
                     (unit, unit_text.encode(), 0o644)])
        target = ENV_DIR / ('temp-monitor-status' if status else 'temp-monitor')
        template = (SOURCE_DIR / (service + '.env')).read_bytes()
        if not target.exists():
            plan.append((target, template, 0o600))
    return services, plan


def apply_plan(services, plan):
    """Restore previous files and running state if installation or health checks fail."""
    originals = {}
    previous = {}
    enabled = {}
    suffix = time.strftime('%Y%m%d_%H%M%S') + '.' + str(os.getpid())
    for service in services:
        enabled[service] = subprocess.run(['systemctl', 'is-enabled', '--quiet', service + '.service'], timeout=10).returncode == 0
        previous[service] = subprocess.run(['systemctl', 'is-active', '--quiet', service + '.service'], timeout=10).returncode == 0
    for path, _, _ in plan:
        originals[path] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
        if originals[path] is not None:
            atomic_write(path.with_name(path.name + '.backup.' + suffix), *originals[path])
    try:
        for path, content, mode in plan:
            atomic_write(path, content, mode)
        run(['systemctl', 'daemon-reload'])
        for service in services:
            run(['systemctl', 'restart', service + '.service'])
        # Catch startup crashes rather than trusting the restart command's exit status.
        for _ in range(3):
            time.sleep(1)
            for service in services:
                run(['systemctl', 'is-active', '--quiet', service + '.service'])
        for service in services:
            run(['systemctl', 'enable', service + '.service'])
    except BaseException:
        for path, original in originals.items():
            if original is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, *original)
        run(['systemctl', 'daemon-reload'])
        for service in services:
            subprocess.run(['systemctl', 'enable' if enabled[service] else 'disable', service + '.service'], timeout=30)
            subprocess.run(['systemctl', 'restart' if previous[service] else 'stop', service + '.service'], timeout=30)
        raise
    for path, _, _ in plan:
        backups = sorted(path.parent.glob(path.name + '.backup.*'), key=lambda item: item.stat().st_mtime, reverse=True)
        for backup in backups[BACKUP_KEEP:]:
            backup.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true', help='Update installed services only')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Please run with sudo')
    if not shutil.which('systemctl'):
        parser.error('systemctl is required')
    try:
        services, plan = build_plan(args.update)
        apply_plan(services, plan)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print('Updated and verified: ' + ', '.join(services))
    print('Existing environment configuration was preserved. Three backups per changed file are retained.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
