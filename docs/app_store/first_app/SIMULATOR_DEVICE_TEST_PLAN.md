# Simulator & Device Test Plan

Procedures to manually evaluate the RMF Companion app binaries:

## Test Scenarios
1. **Launch Test**: Launch app in Simulator. Home screen must render immediately.
2. **Navigation Check**: Click through all 8 screens; verify they transition cleanly.
3. **Storage Persistence**: Mark AC-1 as completed; close and relaunch app. Completion status must persist on-device.
4. **Data Isolation**: Run with network connection disabled/enabled; verify zero network calls are attempted.
