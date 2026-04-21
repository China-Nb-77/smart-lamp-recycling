package com.demo.pay.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "orders")
public class OrderEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String orderId;

    private String traceId;

    private String userId;

    private String contactName;

    private String contactPhone;

    private String addressRegion;

    private String fullAddress;

    private Double receiverLongitude;

    private Double receiverLatitude;

    private String locationSource;

    private String addressSource;

    private String accessDomain;

    private Integer payableTotal;

    private String amountCurrency;

    private String amountUnit;

    @Column(nullable = false)
    private String status;

    private String paymentStatus;

    @Column(unique = true)
    private String idempotentKey;

    @Lob
    @Column(columnDefinition = "TEXT")
    private String snapshotJson;

    private Integer paidAmountTotal;

    private LocalDateTime paidAt;

    private String qrTokenHash;

    private LocalDateTime qrExpiresAt;

    private String qrStatus;

    private String waybillId;

    private String waybillStatus;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
