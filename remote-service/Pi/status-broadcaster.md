# Raspberry Pi status broadcaster

See [the status guide](../../README-STATUS.md) for installation, settings,
diagnostics, and update behavior.

`sudo ./install.sh` installs both temperature and status services. Use
`sudo ./update.sh` to update installed services after pulling repository changes.

Status broadcasts use UDP 9876, while HTTP status diagnostics use TCP 9878 and
bind to loopback by default. Package/git checks run every ten minutes; cached
status is broadcast every minute. The cyan dot reports uncommitted repository
changes, not available upstream commits.
