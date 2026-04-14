package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class WechatPrepayRequest {

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("order_id")
    private String orderId;

    private Integer amount;

    @JsonProperty("idempotent_key")
    private String idempotentKey;

    private String openid;

    @JsonProperty("trade_type")
    private String tradeType;

    @JsonProperty("payer_client_ip")
    private String payerClientIp;

    @JsonProperty("return_url")
    private String returnUrl;

    @JsonProperty("app_name")
    private String appName;

    @JsonProperty("app_url")
    private String appUrl;
}
