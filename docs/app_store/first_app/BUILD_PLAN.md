# Build Plan — RMF Evidence Review Companion

Technical stack and compilation pipeline details:

## Stack
* **Framework**: Flutter (cross-platform iOS and macOS compilation)
* **Local Database**: SQLite (via `sqflite` or `drift` package)
* **Target Platforms**: macOS 13+, iOS 16+

## Build Stages
1. **Bootstrap Project**: Initialize Flutter directory.
2. **Develop UI families**: Form checklist grids.
3. **QA check**: Run unit tests.
4. **Compile App**: Execute `flutter build ipa` and `flutter build macos`.
