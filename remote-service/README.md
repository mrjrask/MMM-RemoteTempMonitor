# Remote Temperature Monitor Services

Choose the installer for your platform:

- `Pi/` - Raspberry Pi broadcaster (systemd service)
- `Mac/` - macOS broadcaster (LaunchDaemon)
- `Windows/` - Windows broadcaster (Scheduled Task)

Each platform folder includes its own README with installation instructions.


## Installer shortcut

On Raspberry Pi devices, you can run the repository-level remote-service installer shortcut:

```bash
cd remote-service
sudo ./install.sh
```

The shortcut dispatches to `Pi/install.sh` on Raspberry Pi OS. On other platforms, use the platform folder listed above.
