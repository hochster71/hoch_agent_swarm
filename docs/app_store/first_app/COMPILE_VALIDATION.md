# Compile Validation & Onboarding

Local toolchains (Flutter & Xcode) were detected as uninstalled or blocked during agent container execution. Below are the steps required for Michael to compile the package on his primary macOS system:

## 1. Setup Instructions
1. Download Flutter SDK from [flutter.dev](https://flutter.dev).
2. Install Xcode via the Mac App Store.
3. Configure iOS toolchain options:
   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -runFirstLaunch
   ```

## 2. Command Execution Sequence
```bash
cd apps/rmf_evidence_review_companion
flutter pub get
flutter analyze
flutter test
flutter build ios --debug --no-codesign
```
