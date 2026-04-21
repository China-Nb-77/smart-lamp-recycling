# QR Payment Flow Script

## Script

Use:

`tools/test-qr-payment-flow.ps1`

## What it does

1. Calls `POST /create_order`
2. Calls `POST /api/v1/orders/{orderId}/qr`
3. Calls `POST /pay/prepay`
4. Calls `POST /wechat/notify`
5. Calls `GET /get_order`
6. Calls `GET /order-view`

## Example

```powershell
cd "C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\AILightShell"
powershell -ExecutionPolicy Bypass -File .\tools\test-qr-payment-flow.ps1
```

## Successful result

- `order_status=PAID`
- `public_view_status=PAID` or the expected order state from the electronic order view
- Printed `qr_content` can be opened on a mobile browser
