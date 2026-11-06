# Delta South Evangelism — Native Android App

This is the standalone Kotlin/Jetpack Compose Android client for the existing Delta South Evangelism service. It is developed separately from the Flask website and does not replace or modify the live backend.

## App identity

- Application ID: ng.mcn.deltasouth.evangelism
- Display name: Delta South Evangelism
- Backend: https://mcn-delta-south.naijacloud.app/
- Kotlin + Jetpack Compose
- JDK 17, Gradle 8.10, Android Gradle Plugin 8.7.3, Android SDK 35
- Minimum Android version: Android 8.0 (API 26)

## Current native capabilities

- Authenticated sign-in using the existing server session.
- Encrypted persistent session cookies and encrypted, account-separated offline GET cache.
- Session restoration after app restart.
- Member profile display and contact-detail updates, password change, membership ID card.
- Attendance history and attendance-register workflows according to server role permissions.
- Giving history, announcements, events, notifications and member-care messaging.
- Church/circuit directory, membership records and statistics.
- Conference tools, finance, reconciliation, reports, governance, account requests, approvals and system/security screens exposed by the current server API.
- Online connectivity indicator and Android back navigation to Home.
- Bounded connection, read, write and total-call timeouts to prevent requests hanging indefinitely.

## Offline behaviour and safety

The app can display previously fetched, allowlisted JSON GET data while offline. Cached data is encrypted and keyed to the authenticated session. Logout clears the local session and offline cache.

Offline changes are not queued or replayed. Attendance, financial actions, approvals and other writes require an internet connection and a live server response. This avoids silently duplicating payments or records when connectivity returns. Server-side authorization remains authoritative.

## Build and release

GitHub Actions workflow: .github/workflows/build-apk.yml.

A push to native-android-development affecting android/** or the workflow triggers:
- Debug APK build and package-signature verification.
- Release Android App Bundle build and ZIP integrity check.
- SHA-256 checksum generation.
- Upload of APK, AAB and checksum artifacts to the workflow run.

The debug APK is installable for testing. A Play Store release AAB must be signed with the app's private upload/release key. Configure these GitHub Actions repository secrets to enable release signing:

- ANDROID_KEYSTORE_BASE64
- ANDROID_KEYSTORE_PATH (the workflow sets the path to its temporary key file)
- ANDROID_KEYSTORE_PASSWORD
- ANDROID_KEY_ALIAS
- ANDROID_KEY_PASSWORD

Keep the keystore and passwords private; never commit them to the repository. If signing secrets are absent, the AAB is built unsigned and is not Play Store-ready.

## Phone-only workflow

No local Android Studio installation is required to produce CI artifacts. Open the repository's GitHub Actions page on the phone, select the Android build workflow, and download the APK/AAB artifacts after a successful run. Install the debug APK only for testing. Use the signed AAB for Play Console upload after configuring the private signing key.

## Protected production boundary

All native client work is isolated on native-android-development. The production main branch, Flask application and live diocesan database are not modified by this Android client workflow. Test all role-specific screens on real devices before public release.


## Android 1.4.1 menu repair

- Version: 1.4.1 (versionCode 6).
- Fixed the Android WebView public-menu double-toggle by removing the duplicate native touch handler. The homepage click handler is now the sole menu toggle controller.
- The Android APK build workflow packages an installable debug APK for on-device verification.
