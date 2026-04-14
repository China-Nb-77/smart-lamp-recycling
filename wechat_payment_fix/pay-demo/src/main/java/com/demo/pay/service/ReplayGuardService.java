package com.demo.pay.service;

import com.demo.pay.exception.BusinessException;
import com.demo.pay.util.SecurityUtil;
import com.demo.pay.util.ValidationUtil;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class ReplayGuardService {

    private static final long EXPIRE_SECONDS = 300;
    private final ConcurrentHashMap<String, Long> nonceCache = new ConcurrentHashMap<>();

    public void validate(String orderId, String token, String timestamp, String nonce, String signature) {
        ValidationUtil.requireNotBlank(timestamp, "timestamp");
        ValidationUtil.requireNotBlank(nonce, "nonce");
        ValidationUtil.requireNotBlank(signature, "signature");
        ValidationUtil.maxLength(nonce, 128, "nonce");

        long requestTs;
        try {
            requestTs = Long.parseLong(timestamp);
        } catch (NumberFormatException ex) {
            throw new BusinessException(401, "QR_TOKEN_INVALID");
        }

        long now = Instant.now().getEpochSecond();
        if (Math.abs(now - requestTs) > EXPIRE_SECONDS) {
            throw new BusinessException(410, "QR_TOKEN_EXPIRED");
        }

        String expected = SecurityUtil.buildReplaySignature(orderId, token, timestamp, nonce);
        if (!expected.equals(signature)) {
            throw new BusinessException(401, "QR_TOKEN_INVALID");
        }

        cleanup(now);
        String cacheKey = orderId + ":" + nonce;
        Long existing = nonceCache.putIfAbsent(cacheKey, now);
        if (existing != null && now - existing <= EXPIRE_SECONDS) {
            throw new BusinessException(401, "QR_TOKEN_INVALID");
        }
    }

    private void cleanup(long now) {
        Iterator<Map.Entry<String, Long>> iterator = nonceCache.entrySet().iterator();
        while (iterator.hasNext()) {
            Map.Entry<String, Long> entry = iterator.next();
            if (now - entry.getValue() > EXPIRE_SECONDS) {
                iterator.remove();
            }
        }
    }
}
