package com.example.demo.controller;

import com.example.demo.entity.*;
import com.example.demo.repository.WaybillRepository;
import com.example.demo.repository.TicketRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@RestController
@RequestMapping("/api")
public class FulfillmentController {

    @Autowired
    private WaybillRepository waybillRepository;
    
    @Autowired
    private TicketRepository ticketRepository;
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    private String generateTraceId() {
        return "TRACE_" + UUID.randomUUID().toString().substring(0, 8);
    }

    @PostMapping("/waybill")
    public Map<String, Object> createWaybill(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        String orderId = (String) request.get("order_id");
        
        String waybillId = "WB" + System.currentTimeMillis() % 1000000;
        
        Waybill waybill = new Waybill();
        waybill.setWaybillId(waybillId);
        waybill.setOrderId(orderId);
        waybill.setStatus(WaybillStatus.CREATED);
        waybill.setCreatedAt(LocalDateTime.now());
        waybill.setUpdatedAt(LocalDateTime.now());
        
        List<Map<String, String>> events = generateRealEvents();
        
        try {
            waybill.setEvents(objectMapper.writeValueAsString(events));
        } catch (Exception e) {
            waybill.setEvents("[]");
        }
        
        waybillRepository.save(waybill);
        
        Map<String, Object> response = new HashMap<>();
        response.put("waybill_id", waybill.getWaybillId());
        response.put("status", waybill.getStatus().toString());
        response.put("trace_id", traceId);
        return response;
    }

    @GetMapping("/track")
    public Map<String, Object> getTrackLogistics(@RequestParam String waybillId) {
        String traceId = generateTraceId();
        
        Optional<Waybill> waybillOpt = waybillRepository.findByWaybillId(waybillId);
        
        Map<String, Object> response = new HashMap<>();
        response.put("waybill_id", waybillId);
        
        if (waybillOpt.isPresent()) {
            Waybill waybill = waybillOpt.get();
            try {
                List<Map<String, String>> events = objectMapper.readValue(
                    waybill.getEvents(), 
                    new TypeReference<List<Map<String, String>>>() {}
                );
                response.put("events", events);
            } catch (Exception e) {
                response.put("events", new ArrayList<>());
            }
            response.put("status", waybill.getStatus().toString());
        } else {
            response.put("events", new ArrayList<>());
            response.put("status", "NOT_FOUND");
        }
        
        response.put("trace_id", traceId);
        return response;
    }

    @PostMapping("/ticket")
    public Map<String, Object> openTicket(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        
        String ticketId = "TCK" + System.currentTimeMillis() % 1000000;
        String orderId = (String) request.get("order_id");
        String waybillId = (String) request.get("waybill_id");
        String reason = (String) request.get("reason");
        String detail = (String) request.get("detail");
        
        List<String> validReasons = Arrays.asList(
            "识别不确定", "地址不全", "支付异常", "轨迹异常", "其他"
        );
        if (reason == null || !validReasons.contains(reason)) {
            reason = "其他";
        }
        
        Ticket ticket = new Ticket();
        ticket.setTicketId(ticketId);
        ticket.setOrderId(orderId);
        if (waybillId != null) {
            ticket.setWaybillId(waybillId);
        }
        ticket.setReason(reason);
        if (detail != null) {
            ticket.setDetail(detail);
        }
        ticket.setStatus(TicketStatus.OPEN);
        ticket.setCreatedAt(LocalDateTime.now());
        
        ticketRepository.save(ticket);
        
        Map<String, Object> response = new HashMap<>();
        response.put("ticket_id", ticketId);
        response.put("status", ticket.getStatus().toString());
        response.put("reason", reason);
        response.put("trace_id", traceId);
        return response;
    }
    
    @GetMapping("/order/{orderId}/waybill")
    public Map<String, Object> getWaybillByOrderId(@PathVariable String orderId) {
        String traceId = generateTraceId();
        
        Optional<Waybill> waybillOpt = waybillRepository.findByOrderId(orderId);
        
        Map<String, Object> response = new HashMap<>();
        response.put("order_id", orderId);
        
        if (waybillOpt.isPresent()) {
            response.put("waybill_id", waybillOpt.get().getWaybillId());
            response.put("status", waybillOpt.get().getStatus().toString());
        } else {
            response.put("waybill_id", null);
            response.put("status", "NOT_FOUND");
        }
        
        response.put("trace_id", traceId);
        return response;
    }
    
    @PostMapping("/waybill/{waybillId}/advance")
    public Map<String, Object> advanceWaybillStatus(@PathVariable String waybillId) {
        String traceId = generateTraceId();
        
        Optional<Waybill> waybillOpt = waybillRepository.findByWaybillId(waybillId);
        
        Map<String, Object> response = new HashMap<>();
        response.put("waybill_id", waybillId);
        
        if (waybillOpt.isPresent()) {
            Waybill waybill = waybillOpt.get();
            WaybillStatus currentStatus = waybill.getStatus();
            WaybillStatus nextStatus = currentStatus;
            
            switch (currentStatus) {
                case CREATED:
                    nextStatus = WaybillStatus.SCHEDULED;
                    break;
                case SCHEDULED:
                    nextStatus = WaybillStatus.IN_TRANSIT;
                    break;
                case IN_TRANSIT:
                    nextStatus = WaybillStatus.DONE;
                    break;
                default:
                    response.put("message", "已经是最终状态，无法推进");
                    response.put("trace_id", traceId);
                    return response;
            }
            
            waybill.setStatus(nextStatus);
            waybill.setUpdatedAt(LocalDateTime.now());
            
            try {
                List<Map<String, String>> events = objectMapper.readValue(
                    waybill.getEvents(), 
                    new TypeReference<List<Map<String, String>>>() {}
                );
                
                String desc = "";
                switch (nextStatus) {
                    case SCHEDULED:
                        desc = "已调度，快递员即将上门";
                        break;
                    case IN_TRANSIT:
                        desc = "包裹已揽收，正在运输中";
                        break;
                    case DONE:
                        desc = "已签收，订单完成";
                        break;
                    default:
                        desc = "状态已更新";
                }
                
                Map<String, String> newEvent = new HashMap<>();
                newEvent.put("eventTime", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
                newEvent.put("status", nextStatus.toString());
                newEvent.put("desc", desc);
                events.add(newEvent);
                
                waybill.setEvents(objectMapper.writeValueAsString(events));
            } catch (Exception e) {
                // 忽略
            }
            
            waybillRepository.save(waybill);
            
            response.put("status", waybill.getStatus().toString());
            response.put("message", "状态已推进到: " + nextStatus);
        } else {
            response.put("status", "NOT_FOUND");
            response.put("message", "运单不存在");
        }
        
        response.put("trace_id", traceId);
        return response;
    }
    
    @PostMapping("/payment/success")
    public Map<String, Object> onPaymentSuccess(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        String orderId = (String) request.get("order_id");
        
        Map<String, Object> waybillRequest = new HashMap<>();
        waybillRequest.put("order_id", orderId);
        Map<String, Object> waybillResponse = createWaybill(waybillRequest);
        
        Map<String, Object> response = new HashMap<>();
        response.put("code", "SUCCESS");
        response.put("message", "支付通知已接收，运单已创建");
        response.put("waybill_id", waybillResponse.get("waybill_id"));
        response.put("trace_id", traceId);
        return response;
    }
    
    @PostMapping("/exception/trigger")
    public Map<String, Object> triggerException(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        String type = (String) request.get("type");
        String orderId = (String) request.get("order_id");
        String detail = (String) request.get("detail");
        
        String reason = "其他";
        if (type != null) {
            switch (type) {
                case "LOW_CONFIDENCE":
                    reason = "识别不确定";
                    break;
                case "ADDRESS_INCOMPLETE":
                    reason = "地址不全";
                    break;
                case "PAYMENT_FAILED":
                    reason = "支付异常";
                    break;
                case "TRACK_EMPTY":
                    reason = "轨迹异常";
                    break;
            }
        }
        
        Map<String, Object> ticketRequest = new HashMap<>();
        ticketRequest.put("order_id", orderId);
        ticketRequest.put("reason", reason);
        ticketRequest.put("detail", detail);
        
        return openTicket(ticketRequest);
    }
    
    private List<Map<String, String>> generateRealEvents() {
        List<Map<String, String>> events = new ArrayList<>();
        
        Map<String, String> event1 = new HashMap<>();
        event1.put("eventTime", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        event1.put("status", "CREATED");
        event1.put("desc", "订单已创建，等待揽收");
        events.add(event1);
        
        Map<String, String> event2 = new HashMap<>();
        event2.put("eventTime", LocalDateTime.now().plusHours(2).format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        event2.put("status", "SCHEDULED");
        event2.put("desc", "已调度，快递员即将上门");
        events.add(event2);
        
        Map<String, String> event3 = new HashMap<>();
        event3.put("eventTime", LocalDateTime.now().plusHours(5).format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        event3.put("status", "IN_TRANSIT");
        event3.put("desc", "包裹已揽收，正在运输中");
        events.add(event3);
        
        Map<String, String> event4 = new HashMap<>();
        event4.put("eventTime", LocalDateTime.now().plusDays(1).format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
        event4.put("status", "DONE");
        event4.put("desc", "已签收，订单完成");
        events.add(event4);
        
        return events;
    }
}