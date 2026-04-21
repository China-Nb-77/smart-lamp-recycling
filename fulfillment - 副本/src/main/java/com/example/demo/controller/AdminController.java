package com.example.demo.controller;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.demo.entity.AdminLog;
import com.example.demo.entity.AdminUser;
import com.example.demo.entity.AppUser;
import com.example.demo.entity.ChatHistory;
import com.example.demo.entity.Ticket;
import com.example.demo.entity.Waybill;
import com.example.demo.repository.AdminLogRepository;
import com.example.demo.repository.AdminUserRepository;
import com.example.demo.repository.AppUserRepository;
import com.example.demo.repository.ChatHistoryRepository;
import com.example.demo.repository.TicketRepository;
import com.example.demo.repository.WaybillRepository;
import com.example.demo.service.SessionTokenService;
import com.example.demo.service.SessionTokenService.SessionPrincipal;

import jakarta.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminUserRepository adminUserRepository;
    private final AdminLogRepository adminLogRepository;
    private final WaybillRepository waybillRepository;
    private final TicketRepository ticketRepository;
    private final AppUserRepository appUserRepository;
    private final ChatHistoryRepository chatHistoryRepository;
    private final SessionTokenService sessionTokenService;

    public AdminController(
        AdminUserRepository adminUserRepository,
        AdminLogRepository adminLogRepository,
        WaybillRepository waybillRepository,
        TicketRepository ticketRepository,
        AppUserRepository appUserRepository,
        ChatHistoryRepository chatHistoryRepository,
        SessionTokenService sessionTokenService
    ) {
        this.adminUserRepository = adminUserRepository;
        this.adminLogRepository = adminLogRepository;
        this.waybillRepository = waybillRepository;
        this.ticketRepository = ticketRepository;
        this.appUserRepository = appUserRepository;
        this.chatHistoryRepository = chatHistoryRepository;
        this.sessionTokenService = sessionTokenService;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> request, HttpServletRequest servletRequest) {
        String username = request.getOrDefault("username", "").trim();
        String password = request.getOrDefault("password", "").trim();
        Optional<AdminUser> userOpt = adminUserRepository.findByUsername(username);
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "用户名或密码错误"));
        }
        AdminUser user = userOpt.get();
        if (!password.equals(user.getPassword()) || user.getStatus() == null || user.getStatus() != 1) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "用户名或密码错误"));
        }

        user.setLastLoginTime(LocalDateTime.now());
        adminUserRepository.save(user);

        SessionPrincipal principal = new SessionPrincipal(user.getId(), user.getUsername(), user.getRole(), "admin_user");
        String token = sessionTokenService.issueAccessToken(principal);

        AdminLog log = new AdminLog();
        log.setUserId(user.getId());
        log.setUsername(user.getUsername());
        log.setOperation("登录");
        log.setMethod("POST");
        log.setParams("admin/login");
        log.setIp(servletRequest.getRemoteAddr());
        log.setCreatedAt(LocalDateTime.now());
        adminLogRepository.save(log);

        return ResponseEntity.ok(Map.of(
            "token", token,
            "user", Map.of(
                "id", user.getId(),
                "username", user.getUsername(),
                "realName", user.getRealName(),
                "role", user.getRole()
            )
        ));
    }

    @GetMapping("/stats")
    public ResponseEntity<?> stats(@RequestHeader(value = "Authorization", required = false) String authorization) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        return ResponseEntity.ok(Map.of(
            "orders", waybillRepository.count(),
            "tickets", ticketRepository.count(),
            "users", appUserRepository.count(),
            "records", chatHistoryRepository.count()
        ));
    }

    @GetMapping("/orders")
    public ResponseEntity<?> orders(@RequestHeader(value = "Authorization", required = false) String authorization) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        List<Map<String, Object>> orders = waybillRepository.findAll().stream().map(this::toOrderSummary).collect(Collectors.toList());
        return ResponseEntity.ok(Map.of("list", orders, "total", orders.size()));
    }

    @GetMapping("/orders/{orderId}")
    public ResponseEntity<?> orderDetail(
        @PathVariable String orderId,
        @RequestHeader(value = "Authorization", required = false) String authorization
    ) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        Optional<Waybill> orderOpt = waybillRepository.findByOrderId(orderId);
        if (orderOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "订单不存在"));
        }
        Waybill waybill = orderOpt.get();
        return ResponseEntity.ok(Map.of(
            "orderId", waybill.getOrderId(),
            "waybillId", waybill.getWaybillId(),
            "status", waybill.getStatus() == null ? "" : waybill.getStatus().toString(),
            "createdAt", String.valueOf(waybill.getCreatedAt()),
            "updatedAt", String.valueOf(waybill.getUpdatedAt()),
            "events", waybill.getEvents() == null ? "[]" : waybill.getEvents()
        ));
    }

    @GetMapping("/users")
    public ResponseEntity<?> users(@RequestHeader(value = "Authorization", required = false) String authorization) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        List<Map<String, Object>> users = appUserRepository.findAll().stream().map(this::toUserSummary).collect(Collectors.toList());
        return ResponseEntity.ok(Map.of("list", users, "total", users.size()));
    }

    @PutMapping("/users/{id}")
    public ResponseEntity<?> updateUserStatus(
        @PathVariable Long id,
        @RequestBody Map<String, Object> request,
        @RequestHeader(value = "Authorization", required = false) String authorization
    ) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        Optional<AppUser> userOpt = appUserRepository.findById(id);
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "用户不存在"));
        }
        AppUser user = userOpt.get();
        Object status = request.get("status");
        int nextStatus = status instanceof Number ? ((Number) status).intValue() : Integer.parseInt(String.valueOf(status));
        user.setStatus(nextStatus);
        appUserRepository.save(user);
        return ResponseEntity.ok(Map.of("success", true));
    }

    @GetMapping("/records")
    public ResponseEntity<?> records(@RequestHeader(value = "Authorization", required = false) String authorization) {
        if (requireAdmin(authorization) == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("message", "未授权"));
        }
        List<Map<String, Object>> records = chatHistoryRepository.findAll().stream()
            .map(this::toRecordSummary)
            .collect(Collectors.toList());
        return ResponseEntity.ok(Map.of("list", records, "total", records.size()));
    }

    private Map<String, Object> toOrderSummary(Waybill waybill) {
        Map<String, Object> order = new HashMap<>();
        order.put("orderId", waybill.getOrderId());
        order.put("waybillId", waybill.getWaybillId());
        order.put("status", waybill.getStatus() == null ? "" : waybill.getStatus().toString());
        order.put("createdAt", String.valueOf(waybill.getCreatedAt()));
        return order;
    }

    private Map<String, Object> toUserSummary(AppUser user) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("id", user.getId());
        payload.put("username", user.getUsername());
        payload.put("displayName", user.getDisplayName());
        payload.put("phone", user.getPhone() == null ? "" : user.getPhone());
        payload.put("email", user.getEmail() == null ? "" : user.getEmail());
        payload.put("status", user.getStatus());
        payload.put("createdAt", String.valueOf(user.getCreatedAt()));
        return payload;
    }

    private Map<String, Object> toRecordSummary(ChatHistory history) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("id", history.getId());
        payload.put("sessionId", history.getSessionId());
        payload.put("question", history.getUserQuestion());
        payload.put("answer", history.getAiAnswer());
        payload.put("traceId", history.getTraceId());
        payload.put("createdAt", String.valueOf(history.getCreatedAt()));
        return payload;
    }

    private SessionPrincipal requireAdmin(String authorization) {
        if (authorization == null || authorization.isBlank()) {
            return null;
        }
        String token = authorization.startsWith("Bearer ")
            ? authorization.substring("Bearer ".length()).trim()
            : authorization.trim();
        SessionPrincipal principal = sessionTokenService.resolveAccessToken(token);
        if (principal == null || !"admin_user".equals(principal.getSubjectType())) {
            return null;
        }
        return principal;
    }
}
