# MCN Delta South Diocese — Native Android

This isolated Android application is developed alongside (not instead of) the existing Flask website and backend.

- Package: ng.mcn.deltasouth.evangelism
- Backend: https://mcn-delta-south.naijacloud.app/
- Language/UI: Kotlin + Jetpack Compose
- Build: Gradle 8.9, JDK 17, Android SDK 35

The initial native shell includes sign-in, a session-cookie-aware API client, dashboard refresh, profile data display and announcement-feed connection. Additional native workflows are being migrated incrementally.

## Build
From this directory run: gradle --no-daemon assembleDebug.

GitHub Actions builds a debug APK on pushes to native-android-development affecting android/**, and uploads it as delta-south-native-debug-apk.

## Safety
No existing Flask files, production data, or main-branch history are modified by this Android folder. The app uses the existing authenticated backend; server-side authorization remains authoritative. This is a development build and requires endpoint verification, device testing, and release signing before public distribution.
