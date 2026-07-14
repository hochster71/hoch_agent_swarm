# Restore com.hoch.helm.operations (the supervisor scheduler)

Disabled 2026-07-14 to end a split-brain: it kept a SECOND PersistentScheduler (PID 17807,
started 09:19, pre-fix code) co-writing soak evidence with UNCHAINED rows. The AU-9 chain caught
it. Phase A cannot pass while two schedulers write the same ledgers.

## To restore (when the supervisor is upgraded to chained-write code):
    launchctl bootstrap gui/$(id -u) /Users/michaelhoch/Library/LaunchAgents/com.hoch.helm.operations.plist
    launchctl kickstart -k gui/$(id -u)/com.hoch.helm.operations

## Plist path preserved:
    /Users/michaelhoch/Library/LaunchAgents/com.hoch.helm.operations.plist   (NOT deleted — only unloaded)

## Why it must NOT auto-restart before a rerun:
Its scheduler predates commit 28cb05bd (honest lease release + AU-9 chained ledger). Until the
supervisor runs current code, it will corrupt any soak by co-writing unchained rows.
