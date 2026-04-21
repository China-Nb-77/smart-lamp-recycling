package com.demo.pay.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class OrderSnapshot {

    @JsonProperty("trace_id")
    private String traceId;

    private UserInfo user;

    private AddressInfo address;

    private List<ItemInfo> items;

    @JsonProperty("payable_total")
    private Integer payableTotal;

    private String currency;

    @JsonProperty("amount_unit")
    private String amountUnit;

    @JsonProperty("access_domain")
    private String accessDomain;

    @Data
    public static class UserInfo {
        @JsonProperty("user_id")
        private String userId;

        private String name;
        private String phone;
    }

    @Data
    public static class AddressInfo {
        @JsonProperty("full_address")
        private String fullAddress;

        private String region;

        private String province;

        private String city;

        private String district;

        private String street;

        @JsonProperty("postal_code")
        private String postalCode;

        private Double longitude;

        private Double latitude;

        @JsonProperty("location_source")
        private String locationSource;

        @JsonProperty("address_source")
        private String addressSource;
    }

    @Data
    public static class ItemInfo {
        @JsonProperty("selected_old_sku")
        private String selectedOldSku;

        @JsonProperty("selected_new_sku")
        private String selectedNewSku;

        private Integer qty;
    }
}
