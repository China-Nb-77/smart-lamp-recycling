package com.demo.pay.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "wechat.pay")
public class WechatPayProperties {

    private boolean enabled;
    private boolean allowUnsafeLocalNotify;
    private String merchantId;
    private String appId;
    private String merchantSerialNumber;
    private String privateKeyPath;
    private String apiV3Key;
    private String notifyUrl;
    private String h5AppName;
    private String h5AppUrl;
    private String defaultPayerClientIp = "127.0.0.1";
    private int orderExpireMinutes = 10;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isAllowUnsafeLocalNotify() {
        return allowUnsafeLocalNotify;
    }

    public void setAllowUnsafeLocalNotify(boolean allowUnsafeLocalNotify) {
        this.allowUnsafeLocalNotify = allowUnsafeLocalNotify;
    }

    public String getMerchantId() {
        return normalize(merchantId);
    }

    public void setMerchantId(String merchantId) {
        this.merchantId = merchantId;
    }

    public String getAppId() {
        return normalize(appId);
    }

    public void setAppId(String appId) {
        this.appId = appId;
    }

    public String getMerchantSerialNumber() {
        return normalize(merchantSerialNumber);
    }

    public void setMerchantSerialNumber(String merchantSerialNumber) {
        this.merchantSerialNumber = merchantSerialNumber;
    }

    public String getPrivateKeyPath() {
        return normalize(privateKeyPath);
    }

    public void setPrivateKeyPath(String privateKeyPath) {
        this.privateKeyPath = privateKeyPath;
    }

    public String getApiV3Key() {
        return normalize(apiV3Key);
    }

    public void setApiV3Key(String apiV3Key) {
        this.apiV3Key = apiV3Key;
    }

    public String getNotifyUrl() {
        return normalize(notifyUrl);
    }

    public void setNotifyUrl(String notifyUrl) {
        this.notifyUrl = notifyUrl;
    }

    public String getH5AppName() {
        return normalize(h5AppName);
    }

    public void setH5AppName(String h5AppName) {
        this.h5AppName = h5AppName;
    }

    public String getH5AppUrl() {
        return normalize(h5AppUrl);
    }

    public void setH5AppUrl(String h5AppUrl) {
        this.h5AppUrl = h5AppUrl;
    }

    public String getDefaultPayerClientIp() {
        return normalize(defaultPayerClientIp);
    }

    public void setDefaultPayerClientIp(String defaultPayerClientIp) {
        this.defaultPayerClientIp = defaultPayerClientIp;
    }

    public int getOrderExpireMinutes() {
        return orderExpireMinutes;
    }

    public void setOrderExpireMinutes(int orderExpireMinutes) {
        this.orderExpireMinutes = orderExpireMinutes;
    }

    public boolean isConfigured() {
        return enabled
                && getMerchantId() != null
                && getAppId() != null
                && getMerchantSerialNumber() != null
                && getPrivateKeyPath() != null
                && getApiV3Key() != null;
    }

    private String normalize(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        return normalized.isEmpty() ? null : normalized;
    }
}
