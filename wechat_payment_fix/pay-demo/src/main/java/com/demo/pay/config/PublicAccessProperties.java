package com.demo.pay.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "app.public-access")
public class PublicAccessProperties {

    private String accessDomain;

    public String getAccessDomain() {
        return normalize(accessDomain);
    }

    public void setAccessDomain(String accessDomain) {
        this.accessDomain = accessDomain;
    }

    public String getBaseUrl() {
        return getAccessDomain();
    }

    public void setBaseUrl(String baseUrl) {
        this.accessDomain = baseUrl;
    }

    private String normalize(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.trim();
        if (normalized.isEmpty()) {
            return null;
        }
        return normalized.replaceAll("/+$", "");
    }
}
