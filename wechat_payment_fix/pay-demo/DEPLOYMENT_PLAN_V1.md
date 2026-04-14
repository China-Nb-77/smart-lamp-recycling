# 部署方案 v1

## 1. 当前本地访问现状

- 当前工程为 `wechat_payment_fix/pay-demo`，Spring Boot 服务监听 `8080`，配置文件为 `src/main/resources/application.yml`。
- 本地核心访问方式：
  - `POST /create_order` 创建订单
  - `POST /api/v1/orders/{orderId}/qr` 生成二维码内容
  - `GET /api/v1/orders/{orderId}/view` 查看电子订单，但要求请求头 `X-Request-Timestamp`、`X-Request-Nonce`、`X-Request-Signature`
  - `GET /get_order`、`GET /order/{orderId}` 查看订单摘要
- 原始代码中二维码内容由 `QrCodeService` 生成，路径固定为 `/order-view?order_id=...&token=...`。
- 原始问题有两处：
  - `access_domain` 只来自下单请求体，不传时二维码内容只会返回相对路径
  - 后端没有公开的 `/order-view` 落点，扫码后没有可直接打开的公共入口

## 2. 最小公网访问方案

### 本地开发联调方案

- 本地启动 `pay-demo`，默认访问地址为 `http://localhost:8080`
- 现在默认配置会把二维码基地址兜底为 `http://localhost:8080`
- 本地联调时直接访问：
  - `http://localhost:8080/order-view?order_id={orderId}&token={token}`

### 内网穿透方案（最低配）

- 适合临时演示，最小落地做法是把本机 `8080` 暴露为一个外网域名
- 例子使用 `frp`：
  - 本机 `frpc` 配置见 `deploy/tunnel/frpc.toml.example`
  - 将 `customDomains` 改成你的演示域名
  - 把 `serverAddr` / `serverPort` 改成已准备好的 `frps`
- 穿透打通后，把 `app.public-access.base-url` 改成对应公网地址，例如 `https://pay-demo.example.com`

### 反向代理方案（最低配）

- 适合有云主机或跳板机时使用
- 在一台可公网访问的 Linux 主机上部署 `nginx`
- 将公网域名反代到运行 `pay-demo` 的 `8080`
- 示例配置见 `deploy/nginx/pay-demo.conf`

### 域名接入最小步骤

1. 准备一个可解析到公网入口的域名，例如 `pay-demo.example.com`
2. 若走 nginx：DNS 解析到 nginx 所在主机
3. 若走 frp：域名解析到 `frps`，并保证 `customDomains` 生效
4. 将 `app.public-access.base-url` 配成 `https://pay-demo.example.com`
5. 重启 `pay-demo`

## 3. 需要修改的配置项

### application.yml

```yml
server:
  port: 8080

app:
  public-access:
    base-url: http://localhost:${server.port}
```

### 配置规则

- `app.public-access.base-url`
  - 用途：二维码默认公网访问基地址
  - 本地默认值：`http://localhost:8080`
  - 公网部署时应改为 `https://你的域名`
- `access_domain`
  - 仍保留在下单请求中
  - 优先级高于 `app.public-access.base-url`
  - 适合单订单指定独立访问域名

## 4. 需要修改的代码文件

- `src/main/java/com/demo/pay/config/PublicAccessProperties.java`
  - 新增公网访问配置读取
- `src/main/java/com/demo/pay/service/QrCodeService.java`
  - 二维码链接支持“订单级域名优先，全局 base URL 兜底”
- `src/main/java/com/demo/pay/service/OrderService.java`
  - 创建订单时自动落默认 `access_domain`
- `src/main/java/com/demo/pay/service/ElectronicOrderService.java`
  - 新增 `viewOrderPublic`，对公开入口复用现有电子订单查询逻辑
- `src/main/java/com/demo/pay/controller/PublicOrderViewController.java`
  - 新增公开访问入口 `GET /order-view`
- `src/main/resources/application.yml`
  - 新增 `app.public-access.base-url`

## 5. nginx / 穿透示例

### nginx 反代示例

```nginx
server {
    listen 80;
    server_name pay-demo.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### frp 穿透示例

```toml
serverAddr = "your-frps.example.com"
serverPort = 7000

[[proxies]]
name = "pay-demo-8080"
type = "http"
localIP = "127.0.0.1"
localPort = 8080
customDomains = ["pay-demo.example.com"]
```

## 6. 二维码链接如何切到公网地址

- 现在二维码内容生成规则：
  - 若下单请求传了 `access_domain`，使用该值
  - 否则使用 `app.public-access.base-url`
- 因此切公网只需要两种最小做法二选一：
  - 全局切换：修改 `application.yml` 中 `app.public-access.base-url`
  - 单订单切换：下单时传 `access_domain=https://你的域名`
- 生成结果示例：
  - 本地：`http://localhost:8080/order-view?order_id=...&token=...`
  - 公网：`https://pay-demo.example.com/order-view?order_id=...&token=...`

## 7. 风险点

- 当前公开入口基于 `token` 直接访问，适合演示和最小落地，不适合直接作为生产级强安全方案
- 如果公网域名和实际反代入口不一致，二维码会生成错误地址
- 若反代层未配 HTTPS，移动端扫码时体验和安全性都较差
- 当前数据默认还是内存 H2，重启会丢；若要长期演示，需要切外部数据库

## 8. 如何验证“可公开访问”

1. 启动 `pay-demo`
2. 将 `app.public-access.base-url` 改成你的公网地址并重启
3. 调用 `POST /create_order` 创建订单
4. 从返回值中取 `data.qr.qr_content`
5. 在外部网络设备上直接打开该 URL，或手机扫码打开
6. 看到 `code=0` 且返回电子订单信息，即表示“可公开访问”成立

### 最小验收口径

- 外网设备可以直接打开二维码 URL
- `/order-view` 能返回订单电子版数据
- 返回内容中 `order_id`、`customer_info`、`amount`、`waybill` 等字段可见
