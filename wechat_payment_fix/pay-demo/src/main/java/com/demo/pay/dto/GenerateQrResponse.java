package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class GenerateQrResponse {

    @JsonProperty("order_id")
    private String orderId;

    @JsonProperty("qr_content")
    private String qrContent;

    @JsonProperty("qr_status")
    private String qrStatus;

    @JsonProperty("expires_at")
    private LocalDateTime expiresAt;
}
