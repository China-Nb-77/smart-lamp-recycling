package com.example.demo.controller;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.demo.entity.AppUser;
import com.example.demo.repository.AppUserRepository;
import com.example.demo.service.SessionTokenService;
import com.example.demo.service.SessionTokenService.SessionPrincipal;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AppUserRepository appUserRepository;
    private final SessionTokenService sessionTokenService;

    public AuthController(AppUserRepository appUserRepository, SessionTokenService sessionTokenService) {
        this.appUserRepository = appUserRepository;
        this.sessionTokenService = sessionTokenService;
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody Map<String, String> request) {
        String username = value(request, "username");
        String password = value(request, "password");
        String displayName = value(request, "displayName");
        String phone = value(request, "phone");
        String email = value(request, "email");

        if (username.isBlank() || password.isBlank()) {
            return ResponseEntity.badRequest().body(error("用户名和密码不能为空"));
        }
        if (appUserRepository.findByUsername(username).isPresent()) {
            return ResponseEntity.status(HttpStatus.CONFLICT).body(error("用户名已存在"));
        }

        AppUser user = new AppUser();
        user.setUsername(username);
        user.setPassword(password);
        user.setDisplayName(displayName.isBlank() ? username : displayName);
        user.setPhone(phone);
        user.setEmail(email);
        user.setStatus(1);
        user.setCreatedAt(LocalDateTime.now());
        user.setLastLoginTime(LocalDateTime.now());
        appUserRepository.save(user);

        return ResponseEntity.ok(successWithTokens(user));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> request) {
        String account = value(request, "account");
        String password = value(request, "password");
        Optional<AppUser> userOpt = appUserRepository.findByUsername(account);
        if (userOpt.isEmpty()) {
            userOpt = appUserRepository.findByPhone(account);
        }
        if (userOpt.isEmpty()) {
            userOpt = appUserRepository.findByEmail(account);
        }
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error("账号或密码错误"));
        }
        AppUser user = userOpt.get();
        if (!password.equals(user.getPassword()) || user.getStatus() != 1) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error("账号或密码错误"));
        }

        user.setLastLoginTime(LocalDateTime.now());
        appUserRepository.save(user);
        return ResponseEntity.ok(successWithTokens(user));
    }

    @PostMapping("/refresh")
    public ResponseEntity<?> refresh(@RequestBody Map<String, String> request) {
        String refreshToken = value(request, "refresh_token");
        SessionPrincipal principal = sessionTokenService.resolveRefreshToken(refreshToken);
        if (principal == null || !"app_user".equals(principal.getSubjectType())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error("refresh_token 无效"));
        }
        String accessToken = sessionTokenService.issueAccessToken(principal);
        Map<String, Object> payload = new HashMap<>();
        payload.put("token", accessToken);
        payload.put("refresh_token", refreshToken);
        payload.put("user", Map.of(
            "id", principal.getUserId(),
            "username", principal.getUsername(),
            "role", principal.getRole()
        ));
        return ResponseEntity.ok(payload);
    }

    @GetMapping("/profile")
    public ResponseEntity<?> profile(@RequestHeader(value = "Authorization", required = false) String authorization) {
        SessionPrincipal principal = resolvePrincipal(authorization);
        if (principal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error("未登录"));
        }
        Optional<AppUser> userOpt = appUserRepository.findById(principal.getUserId());
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error("用户不存在"));
        }
        AppUser user = userOpt.get();
        return ResponseEntity.ok(Map.of(
            "id", user.getId(),
            "username", user.getUsername(),
            "displayName", user.getDisplayName(),
            "phone", user.getPhone() == null ? "" : user.getPhone(),
            "email", user.getEmail() == null ? "" : user.getEmail(),
            "status", user.getStatus(),
            "createdAt", String.valueOf(user.getCreatedAt())
        ));
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(
        @RequestHeader(value = "Authorization", required = false) String authorization,
        @RequestBody(required = false) Map<String, String> request
    ) {
        String accessToken = extractBearer(authorization);
        String refreshToken = request == null ? "" : value(request, "refresh_token");
        sessionTokenService.revoke(accessToken, refreshToken);
        return ResponseEntity.ok(Map.of("success", true));
    }

    private SessionPrincipal resolvePrincipal(String authorization) {
        String token = extractBearer(authorization);
        if (token.isBlank()) {
            return null;
        }
        return sessionTokenService.resolveAccessToken(token);
    }

    private String extractBearer(String authorization) {
        if (authorization == null || authorization.isBlank()) {
            return "";
        }
        if (authorization.startsWith("Bearer ")) {
            return authorization.substring("Bearer ".length()).trim();
        }
        return authorization.trim();
    }

    private Map<String, Object> successWithTokens(AppUser user) {
        SessionPrincipal principal = new SessionPrincipal(user.getId(), user.getUsername(), "user", "app_user");
        String token = sessionTokenService.issueAccessToken(principal);
        String refreshToken = sessionTokenService.issueRefreshToken(principal);
        Map<String, Object> payload = new HashMap<>();
        payload.put("token", token);
        payload.put("refresh_token", refreshToken);
        payload.put("user", Map.of(
            "id", user.getId(),
            "username", user.getUsername(),
            "displayName", user.getDisplayName(),
            "role", "user"
        ));
        return payload;
    }

    private Map<String, Object> error(String message) {
        return Map.of("message", message);
    }

    private String value(Map<String, String> request, String key) {
        return request.getOrDefault(key, "").trim();
    }
}
