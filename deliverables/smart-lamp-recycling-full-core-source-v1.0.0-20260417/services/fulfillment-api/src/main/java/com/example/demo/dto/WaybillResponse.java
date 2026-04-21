package com.example.demo.dto;

public class WaybillResponse {
    private String waybillId;
    private String status;

    public WaybillResponse(String waybillId, String status) {
        this.waybillId = waybillId;
        this.status = status;
    }

    public String getWaybillId() { return waybillId; }
    public void setWaybillId(String waybillId) { this.waybillId = waybillId; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}