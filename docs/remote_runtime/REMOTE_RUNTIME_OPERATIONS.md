# Remote Runtime Operations Manual

Operational guidelines:

## Watchdog
* Watchdog runs continuously to verify memory/disk bounds, outputting to `/data/runtime/remote_health.json`.

## Backups
* Execute `./backup.sh` daily to save current ledgers, active registries, and pipeline files.
* Rotate backups older than 14 days.
