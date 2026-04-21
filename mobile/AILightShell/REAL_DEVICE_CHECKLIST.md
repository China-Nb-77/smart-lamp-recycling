# Real Device Checklist

## Network

- Phone and computer must be on the same LAN.
- Current computer LAN IP: `192.168.132.109`
- H5 URL: `http://192.168.132.109:5173`
- API URL: `http://192.168.132.109:8080`

## Start order

1. Start H5 dev server with host binding.
2. Start Spring Boot backend.
3. Start Metro.
4. Install and open the RN app.

## Features to verify

- Home, list, detail, and profile H5 pages load in WebView.
- Upload center can select an image and submit `POST /api/v1/files/upload`.
- Checkout screen can create order, prepay, and notify.
- QR URL points to the configured public domain or current H5 origin.
- Session sync works between RN and H5 profile page.

## Upload edge cases

- JPEG / PNG / WEBP files upload successfully.
- Text files are rejected with `UNSUPPORTED_FILE_TYPE`.
- Files over 10 MB are rejected with `FILE_TOO_LARGE`.

## Public access checks

- If using public deployment, set `PUBLIC_ACCESS_DOMAIN`.
- Verify `/uploads/...` URLs are reachable from a phone browser.
