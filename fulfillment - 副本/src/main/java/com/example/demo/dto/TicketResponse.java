package com.example.demo.dto;

public class TicketResponse {
    private String ticketId;

    public TicketResponse(String ticketId) {
        this.ticketId = ticketId;
    }

    public String getTicketId() { return ticketId; }
    public void setTicketId(String ticketId) { this.ticketId = ticketId; }
}