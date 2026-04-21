package com.demo.pay.util;

public class LogMaskUtil {

    private LogMaskUtil() {
    }

    public static String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    public static String maskName(String name) {
        if (name == null || name.isBlank()) {
            return name;
        }
        if (name.length() == 1) {
            return "*";
        }
        return name.substring(0, 1) + "*".repeat(Math.max(1, name.length() - 1));
    }

    public static String maskAddress(String address) {
        if (address == null || address.isBlank()) {
            return address;
        }
        if (address.length() <= 6) {
            return "***";
        }
        return address.substring(0, 6) + "****";
    }

    public static String maskOpenId(String openId) {
        return maskToken(openId);
    }

    public static String maskToken(String token) {
        if (token == null || token.isBlank()) {
            return token;
        }
        if (token.length() <= 8) {
            return "****";
        }
        return token.substring(0, 4) + "****" + token.substring(token.length() - 4);
    }

    public static String maskSignature(String signature) {
        return maskToken(signature);
    }

    public static String maskNonce(String nonce) {
        return maskToken(nonce);
    }

    public static String maskIdentifier(String value) {
        return maskToken(value);
    }

    public static String maskQrContent(String qrContent) {
        if (qrContent == null || qrContent.isBlank()) {
            return qrContent;
        }
        return qrContent.replaceAll("token=[^&]+", "token=****");
    }

    public static String maskNotifyPayload(String payload) {
        if (payload == null || payload.isBlank()) {
            return payload;
        }
        String masked = payload;
        masked = masked.replaceAll("(\"transaction_id\"\s*:\s*\")[^\"]+(\")", "$1****$2");
        masked = masked.replaceAll("(\"openid\"\s*:\s*\")[^\"]+(\")", "$1****$2");
        masked = masked.replaceAll("(\"out_trade_no\"\s*:\s*\")[^\"]+(\")", "$1****$2");
        return masked;
    }
}
