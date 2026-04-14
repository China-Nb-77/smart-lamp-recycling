package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.math.BigDecimal;
import java.util.Map;

@Data
public class WechatNotifyRequest {

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("order_id")
    private String orderId;

    @JsonProperty("out_trade_no")
    private String outTradeNo;

    @JsonProperty("prepay_id")
    private String prepayId;

    @JsonProperty("transaction_id")
    private String transactionId;

    @JsonProperty("paid_amount_fen")
    private Integer paidAmountFen;

    @JsonProperty("paid_amount")
    private BigDecimal paidAmount;

    @JsonProperty("trade_state")
    private String tradeState;

    private String status;

    @JsonProperty("paid_at")
    private String paidAt;

    @JsonProperty("success_time")
    private String successTime;

    @JsonProperty("mock_paid")
    private Boolean mockPaid;

    @JsonProperty("amount")
    private AmountInfo amountInfo;

    @JsonProperty("payer")
    private PayerInfo payer;

    @JsonProperty("resource")
    private Map<String, Object> resource;

    private String attach;

    @Data
    public static class AmountInfo {
        @JsonProperty("total")
        @JsonAlias("payer_total")
        private Integer total;

        @JsonProperty("currency")
        private String currency;
    }

    @Data
    public static class PayerInfo {
        @JsonProperty("openid")
        private String openid;
    }
}
