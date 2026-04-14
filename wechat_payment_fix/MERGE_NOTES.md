# Merge Notes

## Merge target
Original source root:
C:\Users\ZhuanZ1\Desktop\新建文件夹 (2)\dengju\pay-demo\src\main

## New interfaces
- POST /api/v1/orders/{orderId}/qr
- GET /api/v1/orders/{orderId}/view?token={token}
- GET /track?order_id={orderId}

## Final mergeable files
- pay-demo/src/main/java/com/demo/pay/PayDemoApplication.java
- pay-demo/src/main/java/com/demo/pay/controller/QuoteController.java
- pay-demo/src/main/java/com/demo/pay/controller/OrderController.java
- pay-demo/src/main/java/com/demo/pay/controller/WechatPayController.java
- pay-demo/src/main/java/com/demo/pay/controller/WechatNotifyController.java
- pay-demo/src/main/java/com/demo/pay/controller/FulfillmentController.java
- pay-demo/src/main/java/com/demo/pay/dto/CreateOrderRequest.java
- pay-demo/src/main/java/com/demo/pay/dto/QuoteRequest.java
- pay-demo/src/main/java/com/demo/pay/dto/QuoteResponse.java
- pay-demo/src/main/java/com/demo/pay/dto/WechatPrepayRequest.java
- pay-demo/src/main/java/com/demo/pay/dto/WechatNotifyRequest.java
- pay-demo/src/main/java/com/demo/pay/dto/CreateWaybillRequest.java
- pay-demo/src/main/java/com/demo/pay/dto/ElectronicOrderViewResponse.java
- pay-demo/src/main/java/com/demo/pay/dto/GenerateQrResponse.java
- pay-demo/src/main/java/com/demo/pay/dto/TrackResponse.java
- pay-demo/src/main/java/com/demo/pay/entity/OrderEntity.java
- pay-demo/src/main/java/com/demo/pay/entity/PaymentEntity.java
- pay-demo/src/main/java/com/demo/pay/entity/OrderStatusLog.java
- pay-demo/src/main/java/com/demo/pay/model/OrderSnapshot.java
- pay-demo/src/main/java/com/demo/pay/repository/OrderRepository.java
- pay-demo/src/main/java/com/demo/pay/repository/PaymentRepository.java
- pay-demo/src/main/java/com/demo/pay/repository/OrderStatusLogRepository.java
- pay-demo/src/main/java/com/demo/pay/service/QuoteService.java
- pay-demo/src/main/java/com/demo/pay/service/OrderService.java
- pay-demo/src/main/java/com/demo/pay/service/WechatPayService.java
- pay-demo/src/main/java/com/demo/pay/service/FulfillmentService.java
- pay-demo/src/main/java/com/demo/pay/service/QrCodeService.java
- pay-demo/src/main/java/com/demo/pay/service/ElectronicOrderService.java
- pay-demo/src/main/java/com/demo/pay/service/ReplayGuardService.java
- pay-demo/src/main/java/com/demo/pay/util/ApiResponse.java
- pay-demo/src/main/java/com/demo/pay/util/LogMaskUtil.java
- pay-demo/src/main/java/com/demo/pay/util/SecurityUtil.java
- pay-demo/src/main/java/com/demo/pay/util/ValidationUtil.java
- pay-demo/src/main/java/com/demo/pay/exception/BusinessException.java
- pay-demo/src/main/java/com/demo/pay/exception/GlobalExceptionHandler.java
- pay-demo/pom.xml
- pay-demo/src/test/java/com/demo/pay/PaymentFlowIntegrationTest.java
- pay-demo/src/test/resources/application.yml

## Notify compatibility
This patch supports:
- business normalized notify: order_id, status, paid_amount_fen, paid_at
- mock notify: order_id, transaction_id, paid_amount, mock_paid
- near-official decrypted fields: out_trade_no, transaction_id, trade_state, amount.total, success_time

This patch does not decrypt official WeChat Pay v3 encrypted resource payload.
