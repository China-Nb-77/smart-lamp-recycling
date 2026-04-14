package com.example.demo.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "waybills")
public class Waybill {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String waybillId;
    private String orderId;
    @Enumerated(EnumType.STRING)
    private WaybillStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    @Column(length = 1000)
    private String events;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getWaybillId() { return waybillId; }
    public void setWaybillId(String waybillId) { this.waybillId = waybillId; }
    public String getOrderId() { return orderId; }
    public void setOrderId(String orderId) { this.orderId = orderId; }
    public WaybillStatus getStatus() { return status; }
    public void setStatus(WaybillStatus status) { this.status = status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
    public String getEvents() { return events; }
    public void setEvents(String events) { this.events = events; }
}