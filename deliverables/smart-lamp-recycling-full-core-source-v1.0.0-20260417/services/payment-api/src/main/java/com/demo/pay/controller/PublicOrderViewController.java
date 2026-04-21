package com.demo.pay.controller;

import com.demo.pay.service.ElectronicOrderService;
import com.demo.pay.util.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PublicOrderViewController {

    private final ElectronicOrderService electronicOrderService;

    public PublicOrderViewController(ElectronicOrderService electronicOrderService) {
        this.electronicOrderService = electronicOrderService;
    }

    @GetMapping("/order-view")
    public ApiResponse<?> viewOrder(@RequestParam("order_id") String orderId,
                                    @RequestParam("token") String token) {
        return ApiResponse.success(electronicOrderService.viewOrderPublic(orderId, token));
    }
}
