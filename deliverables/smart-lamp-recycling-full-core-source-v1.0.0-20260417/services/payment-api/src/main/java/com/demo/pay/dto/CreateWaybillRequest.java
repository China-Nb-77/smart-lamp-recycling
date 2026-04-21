package com.demo.pay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class CreateWaybillRequest {

    @JsonProperty("order_id")
    private String orderId;
}
