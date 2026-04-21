package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ElectronicOrderViewResponse {

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("order_id")
    private String orderId;

    private String status;

    @JsonProperty("pay_status")
    private String payStatus;

    @JsonProperty("qr_status")
    private String qrStatus;

    @JsonProperty("customer_info")
    private CustomerInfo customerInfo;

    @JsonProperty("product_info")
    private ProductInfo productInfo;

    private AmountInfo amount;

    private QrInfo qr;

    private WaybillInfo waybill;

    private List<EventInfo> events;

    @Data
    public static class CustomerInfo {
        @JsonProperty("user_id")
        private String userId;
        private String name;
        private String phone;
        private String address;
        private String region;
        private Double longitude;
        private Double latitude;
        @JsonProperty("location_source")
        private String locationSource;
        @JsonProperty("address_source")
        private String addressSource;
    }

    @Data
    public static class ProductInfo {
        private List<ItemInfo> items;
    }

    @Data
    public static class ItemInfo {
        @JsonProperty("selected_old_sku")
        private String selectedOldSku;
        @JsonProperty("selected_new_sku")
        private String selectedNewSku;
        private Integer qty;
    }

    @Data
    public static class AmountInfo {
        @JsonProperty("payable_total")
        private Integer payableTotal;
        @JsonProperty("paid_amount_total")
        private Integer paidAmountTotal;
        private String currency;
        @JsonProperty("amount_unit")
        private String amountUnit;
    }

    @Data
    public static class QrInfo {
        private String content;
        @JsonProperty("expires_at")
        private LocalDateTime expiresAt;
        private String status;
    }

    @Data
    public static class WaybillInfo {
        @JsonProperty("waybill_id")
        private String waybillId;
        private String status;
    }

    @Data
    public static class EventInfo {
        private String time;
        private String desc;
    }
}
