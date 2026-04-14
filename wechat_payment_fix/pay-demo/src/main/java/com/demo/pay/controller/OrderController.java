package com.demo.pay.controller;

import com.demo.pay.dto.CreateOrderRequest;
import com.demo.pay.service.ElectronicOrderService;
import com.demo.pay.service.OrderService;
import com.demo.pay.util.ApiResponse;
import org.springframework.web.bind.annotation.*;

@RestController
public class OrderController {

    private final OrderService orderService;
    private final ElectronicOrderService electronicOrderService;

    public OrderController(OrderService orderService,
                           ElectronicOrderService electronicOrderService) {
        this.orderService = orderService;
        this.electronicOrderService = electronicOrderService;
    }

    @PostMapping({"/create_order", "/orders", "/order/create"})
    public ApiResponse<?> create(@RequestBody CreateOrderRequest request,
                                 @RequestHeader(value = "Idempotent-Key", required = false) String key) {
        String idempotentKey = orderService.resolveIdempotentKey(request, key);
        return ApiResponse.success(orderService.createOrder(request, idempotentKey));
    }

    @GetMapping("/get_order")
    public ApiResponse<?> get(@RequestParam("order_id") String orderId) {
        return ApiResponse.success(orderService.getOrderView(orderId));
    }

    @GetMapping("/order/{orderId}")
    public ApiResponse<?> getByPath(@PathVariable String orderId) {
        return ApiResponse.success(orderService.getOrderView(orderId));
    }

    @PostMapping("/api/v1/orders/{orderId}/qr")
    public ApiResponse<?> generateQr(@PathVariable String orderId,
                                     @RequestHeader("X-User-Phone") String userPhone) {
        return ApiResponse.success(electronicOrderService.generateQr(orderId, userPhone));
    }

    @GetMapping("/api/v1/orders/{orderId}/view")
    public ApiResponse<?> viewOrder(@PathVariable String orderId,
                                    @RequestParam("token") String token,
                                    @RequestHeader("X-Request-Timestamp") String timestamp,
                                    @RequestHeader("X-Request-Nonce") String nonce,
                                    @RequestHeader("X-Request-Signature") String signature) {
        return ApiResponse.success(electronicOrderService.viewOrder(orderId, token, timestamp, nonce, signature));
    }

    @GetMapping("/track")
    public ApiResponse<?> track(@RequestParam("order_id") String orderId) {
        return ApiResponse.success(electronicOrderService.track(orderId));
    }
}
