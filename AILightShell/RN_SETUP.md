# RN Shell Setup

## Current scope

- React Native shell project: `AILightShell`
- H5 project used by WebView shell: `AI灯泡`
- H5 routes used by RN shell:
  - `/home`
  - `/list`
  - `/detail`
  - `/profile`
- Native capability screens:
  - `UploadCenter`
  - `Checkout`

## Default local addresses

- Emulator fallback:
  - H5 dev server: `http://10.0.2.2:5173`
  - Backend API: `http://10.0.2.2:8080`
- Current real-device LAN addresses:
  - H5 dev server: `http://192.168.132.109:5173`
  - Backend API: `http://192.168.132.109:8080`

If you run on a real Android device, replace both values in `src/config/env.ts` with the host machine LAN IP.

## Commands

```powershell
# H5
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\AI灯泡"
D:\抓包\npm.cmd install
D:\抓包\npm.cmd run dev -- --host 0.0.0.0

# Backend
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\wechat_payment_fix\pay-demo"
mvn spring-boot:run

# RN shell
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\AILightShell"
D:\抓包\npm.cmd install
D:\抓包\npm.cmd start
D:\抓包\npm.cmd run android
```

## APK

Debug APK command:

```powershell
D:\抓包\npm.cmd run apk:debug
```

Output path:

`android/app/build/outputs/apk/debug/app-debug.apk`

## Extra docs

- APK notes: `APK_BUILD_NOTES.md`
- Real-device checklist: `REAL_DEVICE_CHECKLIST.md`
- Real-device flow: `REAL_DEVICE_FLOW.md`
- QR payment flow: `QR_PAYMENT_FLOW.md`
