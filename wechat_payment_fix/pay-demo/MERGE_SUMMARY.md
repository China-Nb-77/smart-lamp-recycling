# Merged Backend Summary

Canonical merged backend: `wechat_payment_fix/pay-demo`

## Unified package structure

```text
src/main/java/com/demo/pay
├─ config
│  └─ PublicAccessProperties.java
├─ controller
│  ├─ FulfillmentController.java
│  ├─ OrderController.java
│  ├─ PublicOrderViewController.java
│  ├─ QuoteController.java
│  ├─ WechatNotifyController.java
│  └─ WechatPayController.java
├─ dto
│  ├─ CreateOrderRequest.java
│  ├─ CreateWaybillRequest.java
│  ├─ ElectronicOrderViewResponse.java
│  ├─ GenerateQrResponse.java
│  ├─ QuoteRequest.java
│  ├─ QuoteResponse.java
│  ├─ TrackResponse.java
│  ├─ WechatNotifyRequest.java
│  └─ WechatPrepayRequest.java
├─ entity
│  ├─ OrderEntity.java
│  ├─ OrderStatusLog.java
│  └─ PaymentEntity.java
├─ exception
│  ├─ BusinessException.java
│  └─ GlobalExceptionHandler.java
├─ model
│  └─ OrderSnapshot.java
├─ repository
│  ├─ OrderRepository.java
│  ├─ OrderStatusLogRepository.java
│  └─ PaymentRepository.java
├─ service
│  ├─ ElectronicOrderService.java
│  ├─ FulfillmentService.java
│  ├─ OrderService.java
│  ├─ QrCodeService.java
│  ├─ QuoteService.java
│  ├─ ReplayGuardService.java
│  └─ WechatPayService.java
├─ util
│  ├─ ApiResponse.java
│  ├─ LogMaskUtil.java
│  ├─ SecurityUtil.java
│  └─ ValidationUtil.java
└─ PayDemoApplication.java
```

## Merge decision

- Kept `wechat_payment_fix/pay-demo` as the canonical backend because it already contains the more complete order, QR, fulfillment, and deployment flow.
- `dengju/pay-demo` was used as a reference only for overlap review; duplicate simplified controller and service implementations were not copied into the canonical backend.
- Standardized the public entry config to `app.public-access.access-domain`.

## Public access checklist

- Set `PUBLIC_ACCESS_DOMAIN` to the public HTTPS domain exposed by Nginx or a tunnel.
- Make sure `server.port` matches the local port used by the proxy or tunnel.
- Confirm that `/create_order`, `/pay/prepay`, `/wechat/notify`, and `/order-view` are reachable from the public domain.
- Confirm the QR payload points to the public domain instead of `localhost`.
