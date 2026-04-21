package com.demo.pay.controller;

import com.demo.pay.service.WechatPayService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class WechatNotifyController {

    private final WechatPayService payService;

    public WechatNotifyController(WechatPayService payService) {
        this.payService = payService;
    }

    @PostMapping({"/notify", "/wechat/notify", "/pay/wechat/notify"})
    public ResponseEntity<Map<String, String>> notify(@RequestBody String body,
                                                      @RequestHeader("Wechatpay-Serial") String serial,
                                                      @RequestHeader("Wechatpay-Timestamp") String timestamp,
                                                      @RequestHeader("Wechatpay-Nonce") String nonce,
                                                      @RequestHeader("Wechatpay-Signature") String signature,
                                                      @RequestHeader(value = "Wechatpay-Signature-Type", required = false) String signatureType) {
        try {
            return ResponseEntity.ok(payService.handleNotifyCallback(
                    body, serial, timestamp, nonce, signature, signatureType));
        } catch (Exception ex) {
            Map<String, String> payload = new LinkedHashMap<>();
            payload.put("code", "FAIL");
            payload.put("message", "callback failed");
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(payload);
        }
    }
}
