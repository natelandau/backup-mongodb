## v1.3.1 (2025-08-11)

### Fix

- support ezbak v0.11.4

## v1.3.0 (2025-07-21)

### Feat

- **docker**: build arm64 image (#33)

### Fix

- **backup**: use directory dump instead of archive (#34)

## v1.2.0 (2025-06-30)

### Feat

- migrate to ezbak (#32)

### Fix

- remove unneeded dependencies

## v1.1.0 (2023-12-19)

### Feat

- confirm db is available before backup (#7)

## v1.0.0 (2023-11-08)

### Feat

- AWS support
- implement CRON schedule
- initial commit

### Fix

- respect `TZ` when generating backups
- **schedule**: convert `h:m` to `hh:mm`
- add sample environment variables
