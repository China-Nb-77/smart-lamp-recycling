package com.demo.pay.service;

import com.demo.pay.entity.OrderEntity;
import com.demo.pay.repository.OrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class FulfillmentService {

    private final OrderService orderService;
    private final OrderRepository orderRepository;

    public FulfillmentService(OrderService orderService, OrderRepository orderRepository) {
        this.orderService = orderService;
        this.orderRepository = orderRepository;
    }

    @Transactional
    public Map<String, Object> createWaybill(String orderId) {
        OrderEntity order = orderService.requireOrder(orderId);
        if (!"PAID".equals(order.getStatus())) {
            throw new IllegalStateException("order status must be PAID before create_waybill");
        }

        if (order.getWaybillId() == null) {
            order.setWaybillId("WB" + orderId.replace("ORD", ""));
            order.setWaybillStatus("WAYBILL_CREATED");
            order.setUpdatedAt(LocalDateTime.now());
            orderRepository.save(order);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("order_id", orderId);
        result.put("order_status", order.getStatus());
        result.put("waybill_id", order.getWaybillId());
        result.put("status", order.getWaybillStatus());
        return result;
    }

    public Map<String, Object> getTrackByWaybillId(String waybillId) {
        OrderEntity order = orderRepository.findByWaybillId(waybillId)
                .orElseThrow(() -> new IllegalArgumentException("waybill not found"));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("waybill_id", order.getWaybillId());
        result.put("events", buildEvents(order));
        return result;
    }

    private List<Map<String, Object>> buildEvents(OrderEntity order) {
        List<Map<String, Object>> events = new ArrayList<>();
        events.add(event(order.getCreatedAt(), "CREATED", "Order created"));
        if (order.getPaidAt() != null) {
            events.add(event(order.getPaidAt(), "PAID", "Payment completed"));
        }
        if (order.getWaybillId() != null) {
            events.add(event(order.getUpdatedAt(), order.getWaybillStatus(), "Waybill created"));
        }
        return events;
    }

    private Map<String, Object> event(LocalDateTime time, String status, String msg) {
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("ts", time == null ? null : time.toEpochSecond(ZoneOffset.ofHours(8)));
        event.put("status", status);
        event.put("msg", msg);
        return event;
    }
}
