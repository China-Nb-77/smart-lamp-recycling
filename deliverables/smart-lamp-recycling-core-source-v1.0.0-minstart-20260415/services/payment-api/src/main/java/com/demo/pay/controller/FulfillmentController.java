package com.demo.pay.controller;

import com.demo.pay.dto.CreateWaybillRequest;
import com.demo.pay.service.FulfillmentService;
import com.demo.pay.util.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class FulfillmentController {

    private final FulfillmentService fulfillmentService;

    public FulfillmentController(FulfillmentService fulfillmentService) {
        this.fulfillmentService = fulfillmentService;
    }

    @PostMapping({"/create_waybill", "/fulfillment/waybills"})
    public ApiResponse<?> createWaybill(@RequestBody CreateWaybillRequest request) {
        return ApiResponse.success(fulfillmentService.createWaybill(request.getOrderId()));
    }

    @GetMapping("/api/v1/fulfillment/track/{waybillId}")
    public ApiResponse<?> getTrack(@PathVariable String waybillId) {
        return ApiResponse.success(fulfillmentService.getTrackByWaybillId(waybillId));
    }
}
