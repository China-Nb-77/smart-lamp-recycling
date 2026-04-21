package com.demo.pay.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "payments")
public class PaymentEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String orderId;

    private String traceId;

    @Column(unique = true)
    private String prepayId;

    @Column(unique = true)
    private String transactionId;

    @Column(unique = true)
    private String idempotentKey;

    private String payerOpenid;

    private String tradeType;

    @Column(nullable = false)
    private Integer amountTotal;

    private String amountCurrency;

    private String amountUnit;

    @Column(columnDefinition = "TEXT")
    private String codeUrl;

    @Column(columnDefinition = "TEXT")
    private String h5Url;

    @Column(nullable = false)
    private String status;

    @Lob
    @Column(columnDefinition = "TEXT")
    private String rawPrepayPayload;

    @Lob
    @Column(columnDefinition = "TEXT")
    private String rawNotifyPayload;

    private Integer notifyCount;

    private LocalDateTime paidAt;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
