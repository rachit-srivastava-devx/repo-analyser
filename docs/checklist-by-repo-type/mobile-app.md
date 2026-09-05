# Mobile App Repo (iOS/Android)

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `.xcodeproj`/`.xcworkspace`/`Info.plist` (iOS), `AndroidManifest.xml` + `build.gradle` (Android), or `pubspec.yaml` (Flutter) / `app.json` + Expo config (React Native) | `find . -iname Info.plist -o -iname AndroidManifest.xml` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **Code-signing/provisioning-profile hygiene** | signing certificates and provisioning profiles are managed consistently across every developer and CI runner instead of living as one person's local keychain. | `fastlane match` |
| **Permission-vs-disclosure parity** | every permission the app actually requests at runtime is declared in the store's own privacy disclosure, closing a gap that's both a store-rejection risk and a user-trust issue. | `Play Console Data Safety form`, `App Store Connect App Privacy details` |
| **Secrets never stored in plaintext app sandbox** | tokens and credentials are held in the platform's dedicated secure storage rather than NSUserDefaults/SharedPreferences or a bundled plist/resource file. | `iOS Keychain Services audit`, `Android Keystore audit` |
| **Mobile-specific static + dynamic security scan** | hardcoded keys, exported components, and insecure inter-app communication are scanned for with tooling built for the mobile threat model, not a generic web scanner pointed at a decompiled APK/IPA. | `MobSF` |
| **Target-API currency** | the app targets a recent-enough platform API level to clear the store's rolling minimum-target requirement, checked on a schedule rather than discovered at submission time. | `targetSdkVersion compliance check` |
| **Release-health gating on phased rollout** | a staged rollout is halted automatically once crash-free-rate drops below threshold, instead of a bad build reaching 100% of users before anyone notices. | `Firebase Crashlytics (crash-free-rate thresholds)` |
