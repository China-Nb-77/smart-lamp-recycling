package com.demo.pay.controller;

import com.demo.pay.dto.QuoteRequest;
import com.demo.pay.service.QuoteService;
import com.demo.pay.util.ApiResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class QuoteController {

    private final QuoteService quoteService;

    public QuoteController(QuoteService quoteService) {
        this.quoteService = quoteService;
    }

    @PostMapping("/quote")
    public ApiResponse<?> quote(@RequestBody QuoteRequest request) {
        return ApiResponse.success(quoteService.quote(request));
    }
}
