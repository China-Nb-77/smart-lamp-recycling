# Public Access Deployment

## Application config

Use the merged backend in `wechat_payment_fix/pay-demo` and configure the public domain with:

```yaml
server:
  address: 0.0.0.0
  port: ${SERVER_PORT:8080}
  forward-headers-strategy: framework

app:
  public-access:
    access-domain: ${PUBLIC_ACCESS_DOMAIN:https://pay-demo.example.com}
```

Example startup:

```powershell
$env:SERVER_PORT="8080"
$env:PUBLIC_ACCESS_DOMAIN="https://pay-demo.example.com"
mvn spring-boot:run
```

## Nginx reverse proxy

Use `deploy/nginx/pay-demo.conf` as the baseline and replace:

- `pay-demo.example.com` with the real public domain.
- certificate paths with the real certificate files.

## Tunnel options

FRP example: `deploy/tunnel/frpc.toml.example`

ngrok example: `deploy/tunnel/ngrok.yml.example`

Start ngrok after replacing the token and domain:

```powershell
ngrok start --all --config deploy/tunnel/ngrok.yml.example
```

## Verification

1. Open `https://your-domain/order-view?order_id=...&token=...` from a public network.
2. Call `POST https://your-domain/create_order`.
3. Call `POST https://your-domain/pay/prepay`.
4. Call `POST https://your-domain/wechat/notify`.
5. Confirm the QR payload returned by the backend starts with `https://your-domain/`.
