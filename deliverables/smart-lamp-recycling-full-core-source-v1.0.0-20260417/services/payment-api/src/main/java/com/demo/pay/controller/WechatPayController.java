package com.demo.pay.controller;

import com.demo.pay.dto.WechatPrepayRequest;
import com.demo.pay.service.WechatPayService;
import com.demo.pay.util.ApiResponse;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class WechatPayController {

    private final WechatPayService payService;

    public WechatPayController(WechatPayService payService) {
        this.payService = payService;
    }

    @PostMapping({"/prepay", "/pay/prepay", "/pay/wechat/prepay"})
    public ApiResponse<?> prepay(@RequestBody WechatPrepayRequest request,
                                 @RequestHeader(value = "Idempotent-Key", required = false) String key,
                                 HttpServletRequest servletRequest) {
        return ApiResponse.success(payService.createPrepay(
                request,
                key,
                extractClientIp(servletRequest),
                servletRequest.getHeader("User-Agent")
        ));
    }

    @GetMapping({"/payment/status", "/pay/status"})
    public ApiResponse<?> paymentStatus(@RequestParam("order_id") String orderId,
                                        @RequestParam(value = "sync", defaultValue = "true") boolean sync) {
        return ApiResponse.success(payService.queryPaymentStatus(orderId, sync));
    }

    private String extractClientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            return forwarded.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return realIp.trim();
        }
        return request.getRemoteAddr();
    }
}
