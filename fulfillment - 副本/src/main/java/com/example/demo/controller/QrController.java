package com.example.demo.controller;

import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@RestController
@RequestMapping("/api")
public class QrController {

    private final Map<String, String> tokenOrderMap = new ConcurrentHashMap<>();
    private final Map<String, LocalDateTime> tokenExpiryMap = new ConcurrentHashMap<>();
    
    private String generateTraceId() {
        return "TRACE_" + UUID.randomUUID().toString().substring(0, 8);
    }

    @PostMapping("/qr/generate")
    public Map<String, Object> generateQr(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        String orderId = (String) request.get("order_id");
        
        String qrToken = UUID.randomUUID().toString();
        LocalDateTime expireAt = LocalDateTime.now().plusHours(24);
        
        tokenOrderMap.put(qrToken, orderId);
        tokenExpiryMap.put(qrToken, expireAt);
        
        String qrUrl = "https://yourdomain.com/qr/" + qrToken;
        
        Map<String, Object> response = new HashMap<>();
        response.put("trace_id", traceId);
        response.put("qr_token", qrToken);
        response.put("qr_url", qrUrl);
        response.put("expire_at", expireAt.toString());
        return response;
    }

    @GetMapping("/order/{orderId}/electronic")
    public Map<String, Object> getElectronicOrder(
            @PathVariable String orderId,
            @RequestParam String qrToken) {
        
        String traceId = generateTraceId();
        
        Map<String, Object> response = new HashMap<>();
        response.put("order_id", orderId);
        response.put("trace_id", traceId);
        
        String storedOrderId = tokenOrderMap.get(qrToken);
        if (storedOrderId == null) {
            response.put("code", "INVALID_TOKEN");
            response.put("message", "二维码无效");
            response.put("status_code", 401);
            return response;
        }
        
        if (!storedOrderId.equals(orderId)) {
            response.put("code", "TOKEN_MISMATCH");
            response.put("message", "二维码与订单不匹配");
            response.put("status_code", 401);
            return response;
        }
        
        LocalDateTime expireAt = tokenExpiryMap.get(qrToken);
        if (expireAt == null || expireAt.isBefore(LocalDateTime.now())) {
            response.put("code", "TOKEN_EXPIRED");
            response.put("message", "二维码已过期");
            response.put("status_code", 410);
            return response;
        }
        
        Map<String, Object> orderBasic = new HashMap<>();
        orderBasic.put("order_id", orderId);
        orderBasic.put("status", "PAID");
        orderBasic.put("created_at", "2026-03-30T10:00:00");
        
        List<Map<String, Object>> items = new ArrayList<>();
        Map<String, Object> item = new HashMap<>();
        item.put("sku", "SKU001");
        item.put("name", "智能台灯A");
        item.put("qty", 1);
        item.put("price", 99.00);
        items.add(item);
        
        Map<String, Object> payment = new HashMap<>();
        payment.put("total", 99.00);
        payment.put("pay_status", "PAID");
        payment.put("paid_at", "2026-03-30T10:05:00");
        
        Map<String, Object> waybill = new HashMap<>();
        waybill.put("waybill_id", "WB123456");
        waybill.put("status", "CREATED");
        
        List<Map<String, String>> timeline = new ArrayList<>();
        Map<String, String> t1 = new HashMap<>();
        t1.put("time", "2026-03-30T10:00:00");
        t1.put("event", "订单创建");
        timeline.add(t1);
        
        response.put("code", "SUCCESS");
        response.put("order_basic", orderBasic);
        response.put("items", items);
        response.put("payment", payment);
        response.put("waybill", waybill);
        response.put("timeline", timeline);
        response.put("status_code", 200);
        return response;
    }
    
    @GetMapping("/qr/error")
    public Map<String, Object> getQrError(@RequestParam String code) {
        String traceId = generateTraceId();
        
        Map<String, Object> response = new HashMap<>();
        response.put("trace_id", traceId);
        response.put("error_code", code);
        
        switch (code) {
            case "401":
                response.put("message", "二维码无效，请重新扫描");
                response.put("suggestion", "您可以联系客服获取新二维码");
                break;
            case "404":
                response.put("message", "订单不存在");
                response.put("suggestion", "请确认订单号是否正确");
                break;
            case "410":
                response.put("message", "二维码已过期");
                response.put("suggestion", "请重新生成二维码");
                break;
            default:
                response.put("message", "未知错误");
                response.put("suggestion", "请联系客服");
        }
        return response;
    }
}