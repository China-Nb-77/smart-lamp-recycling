# Real Device Flow

## Step order

1. Run `tools\set-lan-env.ps1 -LanIp 192.168.132.109` if the LAN IP changed.
2. Run `tools\start-local-stack.ps1`.
3. Run `tools\device-smoke-check.ps1 -LanIp 192.168.132.109`.
4. Install the RN app on the device.
5. Open the app and verify tabs:
   - Home
   - List
   - Detail
   - Profile
6. Open Upload Center and test a valid image upload.
7. Run `tools\test-qr-payment-flow.ps1`.
8. Open the printed `qr_content` link on the phone browser.
9. Verify order status and payment status are updated.

## Commands

```powershell
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\AILightShell"
powershell -ExecutionPolicy Bypass -File .\tools\device-smoke-check.ps1 -LanIp 192.168.132.109
powershell -ExecutionPolicy Bypass -File .\tools\test-qr-payment-flow.ps1 -ApiBaseUrl http://192.168.132.109:8080 -AccessDomain http://192.168.132.109:5173
```

## Notes

- If `adb` is not installed, install Android platform-tools or use Android Studio.
- If the phone cannot open the H5 or API addresses, check firewall and that both devices are on the same Wi-Fi.
- Appium automation is not included here because Appium/adb is not currently available in this environment.
