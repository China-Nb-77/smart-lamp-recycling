package com.demo.pay.util;

import com.demo.pay.exception.BusinessException;

public class ValidationUtil {

    private static final String PHONE_PATTERN = "^\\+?[0-9\\-]{6,20}$";
    private static final String POSTAL_CODE_PATTERN = "^[A-Za-z0-9\\-]{4,16}$";

    private ValidationUtil() {
    }

    public static String requireNotBlank(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldName + " is required");
        }
        return value.trim();
    }

    public static String maxLength(String value, int maxLength, String fieldName) {
        if (value != null && value.length() > maxLength) {
            throw new IllegalArgumentException(fieldName + " length overflow");
        }
        return value;
    }

    public static int requirePositive(Integer value, String fieldName) {
        if (value == null || value <= 0) {
            throw new IllegalArgumentException(fieldName + " must be positive");
        }
        return value;
    }

    public static void requireTrue(boolean condition, int status, String errorCode) {
        if (!condition) {
            throw new BusinessException(status, errorCode);
        }
    }

    public static String requirePresentAndNotBlank(String value, String fieldName) {
        return requireNotBlank(value, fieldName);
    }

    public static String validatePhone(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            return value;
        }
        String trimmed = value.trim();
        if (!trimmed.matches(PHONE_PATTERN)) {
            throw new IllegalArgumentException(fieldName + " format invalid");
        }
        return trimmed;
    }

    public static String validatePostalCode(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            return value;
        }
        String trimmed = value.trim();
        if (!trimmed.matches(POSTAL_CODE_PATTERN)) {
            throw new IllegalArgumentException(fieldName + " format invalid");
        }
        return trimmed;
    }

    public static Double validateLongitude(Double value, String fieldName) {
        if (value == null) {
            return null;
        }
        if (value < -180 || value > 180) {
            throw new IllegalArgumentException(fieldName + " out of range");
        }
        return value;
    }

    public static Double validateLatitude(Double value, String fieldName) {
        if (value == null) {
            return null;
        }
        if (value < -90 || value > 90) {
            throw new IllegalArgumentException(fieldName + " out of range");
        }
        return value;
    }
}
