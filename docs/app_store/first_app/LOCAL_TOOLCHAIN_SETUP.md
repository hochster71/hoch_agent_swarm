# Local Toolchain Setup & Verification

Guide to confirm toolchain availability before staging code:

## Verification Checklist
1. **Xcode Command**: Run `xcode-select -p`. Must return path to Developer Directory.
2. **Xcode Version**: Run `xcodebuild -version`.
3. **Flutter Command**: Run `flutter --version`.
4. **Flutter Health**: Run `flutter doctor -v`.
5. **Simulators**: Run `flutter devices`.
