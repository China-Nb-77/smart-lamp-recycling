package com.demo.pay.dto;

import lombok.Data;

import java.util.List;

@Data
public class TrackResponse {
    private List<ElectronicOrderViewResponse.EventInfo> events;
}
