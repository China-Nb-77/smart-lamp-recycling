package com.example.demo.dto;

public class TrackEvent {
    private String eventTime;
    private String status;
    private String desc;

    public TrackEvent(String eventTime, String status, String desc) {
        this.eventTime = eventTime;
        this.status = status;
        this.desc = desc;
    }

    public String getEventTime() { return eventTime; }
    public void setEventTime(String eventTime) { this.eventTime = eventTime; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getDesc() { return desc; }
    public void setDesc(String desc) { this.desc = desc; }
}