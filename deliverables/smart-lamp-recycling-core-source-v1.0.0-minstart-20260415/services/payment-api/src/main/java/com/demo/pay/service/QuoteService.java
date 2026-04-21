package com.demo.pay.service;

import com.demo.pay.dto.QuoteRequest;
import com.demo.pay.dto.QuoteResponse;
import com.demo.pay.util.ValidationUtil;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class QuoteService {

    private static final int UNIT_PRICE_FEN = 1990;

    public QuoteResponse quote(QuoteRequest request) {
        validateQuoteRequest(request);
        int qty = request.getQty() == null || request.getQty() <= 0 ? 1 : request.getQty();
        int payableTotal = Math.multiplyExact(UNIT_PRICE_FEN, qty);

        QuoteResponse.OptionItem option = new QuoteResponse.OptionItem();
        option.setNewSku("NEW-SKU-101");
        option.setName("智能面板灯 600x600 36W");
        option.setDefault(true);

        QuoteResponse.IdentifyInfo identifyInfo = new QuoteResponse.IdentifyInfo();
        identifyInfo.setTopk(List.of(blankToDefault(request.getSelectedOldSku(), "OLD-SKU-001"), "OLD-SKU-002", "OLD-SKU-003"));

        QuoteResponse response = new QuoteResponse();
        response.setTraceId(request.getTraceId());
        response.setQuoteId("Q" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")));
        response.setSelectedOldSku(blankToDefault(request.getSelectedOldSku(), "OLD-SKU-001"));
        response.setSelectedNewSku("NEW-SKU-101");
        response.setQty(qty);
        response.setUnitPrice(UNIT_PRICE_FEN);
        response.setPayableTotal(payableTotal);
        response.setOptions(List.of(option));
        response.setIdentify(identifyInfo);
        response.setNeedMoreInfo(false);
        response.setAsk("");
        return response;
    }

    private void validateQuoteRequest(QuoteRequest request) {
        ValidationUtil.maxLength(request.getTraceId(), 64, "trace_id");
        ValidationUtil.maxLength(request.getUserId(), 64, "user_id");
        ValidationUtil.maxLength(request.getName(), 64, "name");
        ValidationUtil.validatePhone(ValidationUtil.maxLength(request.getPhone(), 32, "phone"), "phone");
        ValidationUtil.maxLength(request.getFullAddress(), 256, "full_address");
        ValidationUtil.maxLength(request.getRegion(), 64, "region");
        ValidationUtil.maxLength(request.getProvince(), 64, "province");
        ValidationUtil.maxLength(request.getCity(), 64, "city");
        ValidationUtil.maxLength(request.getDistrict(), 64, "district");
        ValidationUtil.maxLength(request.getStreet(), 128, "street");
        ValidationUtil.validatePostalCode(ValidationUtil.maxLength(request.getPostalCode(), 32, "postal_code"), "postal_code");
        ValidationUtil.maxLength(request.getLocationSource(), 32, "location_source");
        ValidationUtil.maxLength(request.getAddressSource(), 32, "address_source");
        ValidationUtil.requireTrue((request.getLongitude() == null) == (request.getLatitude() == null), 400, "INVALID_REQUEST");
        ValidationUtil.validateLongitude(request.getLongitude(), "longitude");
        ValidationUtil.validateLatitude(request.getLatitude(), "latitude");
    }

    private String blankToDefault(String value, String defaultValue) {
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        ValidationUtil.maxLength(value, 64, "selected_old_sku");
        return value;
    }
}
