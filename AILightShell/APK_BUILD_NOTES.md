# APK Build Notes

## Current blocker

The project code is ready, but `gradlew.bat assembleDebug` is currently blocked by Gradle distribution download TLS failures from this machine.

## Recommended recovery path

1. Download `gradle-9.0.0-bin.zip` on any machine that can access Gradle.
2. Put the zip here:

`AILightShell/android/gradle-9.0.0-bin.zip`

3. Run:

```powershell
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\AILightShell"
powershell -ExecutionPolicy Bypass -File .\tools\use-local-gradle.ps1
```

4. Build:

```powershell
D:\抓包\npm.cmd run apk:debug
```

## Android SDK checks

- Make sure `ANDROID_HOME` or `ANDROID_SDK_ROOT` points to a valid SDK.
- Make sure `platforms;android-36`, `build-tools;36.0.0`, and `platform-tools` are installed.
- If `adb` is available, verify device connectivity with `adb devices`.

## Expected APK output

`android/app/build/outputs/apk/debug/app-debug.apk`
