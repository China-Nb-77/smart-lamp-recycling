package com.demo.pay.controller;

import com.demo.pay.util.ApiResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class TicketController {

    @PostMapping({"/api/v1/tickets", "/tickets"})
    public ApiResponse<?> openTicket(@RequestBody Map<String, Object> request) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("ticket_id", "TK" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS")));
        result.put("status", "OPEN");
        result.put("trace_id", request.get("order_id"));
        result.put("type", request.get("type"));
        result.put("detail", request.get("detail"));
        return ApiResponse.success(result);
    }
}
