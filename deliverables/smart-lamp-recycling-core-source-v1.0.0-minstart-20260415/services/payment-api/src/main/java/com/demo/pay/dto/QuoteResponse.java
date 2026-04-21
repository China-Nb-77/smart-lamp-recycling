package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
public class QuoteResponse {

    @JsonProperty("trace_id")
    private String traceId;

    @JsonProperty("quote_id")
    private String quoteId;

    @JsonProperty("selected_old_sku")
    private String selectedOldSku;

    @JsonProperty("selected_new_sku")
    private String selectedNewSku;

    private Integer qty;

    @JsonProperty("unit_price")
    private Integer unitPrice;

    @JsonProperty("payable_total")
    private Integer payableTotal;

    private List<OptionItem> options;

    private IdentifyInfo identify;

    @JsonProperty("need_more_info")
    private boolean needMoreInfo;

    private String ask;

    @Data
    public static class OptionItem {
        @JsonProperty("new_sku")
        private String newSku;
        private String name;
        @JsonProperty("is_default")
        private boolean isDefault;
    }

    @Data
    public static class IdentifyInfo {
        private List<String> topk;
    }
}
