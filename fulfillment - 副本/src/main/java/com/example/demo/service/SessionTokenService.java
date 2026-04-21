package com.example.demo.service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Service;

@Service
public class SessionTokenService {

    public static class SessionPrincipal {
        private final Long userId;
        private final String username;
        private final String role;
        private final String subjectType;
        private final LocalDateTime createdAt;

        public SessionPrincipal(Long userId, String username, String role, String subjectType) {
            this.userId = userId;
            this.username = username;
            this.role = role;
            this.subjectType = subjectType;
            this.createdAt = LocalDateTime.now();
        }

        public Long getUserId() { return userId; }
        public String getUsername() { return username; }
        public String getRole() { return role; }
        public String getSubjectType() { return subjectType; }
        public LocalDateTime getCreatedAt() { return createdAt; }
    }

    private final Map<String, SessionPrincipal> accessTokens = new ConcurrentHashMap<>();
    private final Map<String, SessionPrincipal> refreshTokens = new ConcurrentHashMap<>();

    public String issueAccessToken(SessionPrincipal principal) {
        String token = UUID.randomUUID().toString().replace("-", "");
        accessTokens.put(token, principal);
        return token;
    }

    public String issueRefreshToken(SessionPrincipal principal) {
        String token = UUID.randomUUID().toString().replace("-", "");
        refreshTokens.put(token, principal);
        return token;
    }

    public SessionPrincipal resolveAccessToken(String token) {
        return accessTokens.get(token);
    }

    public SessionPrincipal resolveRefreshToken(String token) {
        return refreshTokens.get(token);
    }

    public void revoke(String accessToken, String refreshToken) {
        if (accessToken != null && !accessToken.isBlank()) {
            accessTokens.remove(accessToken);
        }
        if (refreshToken != null && !refreshToken.isBlank()) {
            refreshTokens.remove(refreshToken);
        }
    }
}
