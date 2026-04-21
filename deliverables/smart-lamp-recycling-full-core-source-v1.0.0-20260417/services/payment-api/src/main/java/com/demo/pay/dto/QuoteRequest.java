package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.Map;

@Data
public class QuoteRequest {

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("selected_old_sku")
    private String selectedOldSku;

    @JsonProperty("user_id")
    private String userId;

    private String name;

    private String phone;

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

    private Integer qty;

    private Map<String, Object> prefs;
}
