package com.demo.pay.service;

import com.demo.pay.config.PublicAccessProperties;
import com.demo.pay.dto.GenerateQrResponse;
import com.demo.pay.entity.OrderEntity;
import com.demo.pay.exception.BusinessException;
import com.demo.pay.util.SecurityUtil;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class QrCodeService {

    private static final int QR_EXPIRE_DAYS = 7;
    private final PublicAccessProperties publicAccessProperties;

    public QrCodeService(PublicAccessProperties publicAccessProperties) {
        this.publicAccessProperties = publicAccessProperties;
    }

    public GenerateQrResponse createOrRefresh(OrderEntity order) {
        String token = SecurityUtil.randomToken();
        order.setQrTokenHash(SecurityUtil.sha256Hex(token));
        order.setQrExpiresAt(LocalDateTime.now().plusDays(QR_EXPIRE_DAYS));
        order.setQrStatus("ACTIVE");
        order.setUpdatedAt(LocalDateTime.now());
        return buildResponse(order, token);
    }

    public void validateToken(OrderEntity order, String token) {
        if (order == null) {
            throw new BusinessException(404, "ORDER_NOT_FOUND");
        }
        if (order.getQrExpiresAt() == null || order.getQrExpiresAt().isBefore(LocalDateTime.now())) {
            order.setQrStatus("EXPIRED");
            throw new BusinessException(410, "QR_TOKEN_EXPIRED");
        }
        String tokenHash = SecurityUtil.sha256Hex(token);
        if (order.getQrTokenHash() == null || !order.getQrTokenHash().equals(tokenHash)) {
            throw new BusinessException(401, "QR_TOKEN_INVALID");
        }
    }

    public GenerateQrResponse buildResponse(OrderEntity order, String token) {
        GenerateQrResponse response = new GenerateQrResponse();
        response.setOrderId(order.getOrderId());
        response.setQrContent(buildOrderViewLink(order, token));
        response.setQrStatus(order.getQrStatus());
        response.setExpiresAt(order.getQrExpiresAt());
        return response;
    }

    public String buildOrderViewLink(OrderEntity order, String token) {
        String path = buildOrderViewLink(order.getOrderId(), token);
        String accessDomain = resolveAccessDomain(order);
        if (accessDomain == null || accessDomain.isBlank()) {
            return path;
        }
        return accessDomain + path;
    }

    public String buildOrderViewLink(String orderId, String token) {
        return "/order-view?order_id=" + orderId + "&token=" + token;
    }

    public String resolveAccessDomain(OrderEntity order) {
        if (order.getAccessDomain() != null && !order.getAccessDomain().isBlank()) {
            return order.getAccessDomain().trim().replaceAll("/+$", "");
        }
        return publicAccessProperties.getAccessDomain();
    }
}
