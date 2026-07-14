# Restore com.hoch.helm-autoloop
Disabled 2026-07-14: its 5s health loop spawns a COMPETING uvicorn on 0.0.0.0:8770 if the check
fails, fighting the real helm_live_api on 127.0.0.1:8770. A single API must own the port.
## Restore: launchctl bootstrap gui/$(id -u) /Users/michaelhoch/Library/LaunchAgents/com.hoch.helm-autoloop.plist
## Plist PRESERVED, not deleted: /Users/michaelhoch/Library/LaunchAgents/com.hoch.helm-autoloop.plist
