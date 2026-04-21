package com.demo.pay.service;

import com.demo.pay.config.PublicAccessProperties;
import com.demo.pay.config.WechatPayProperties;
import com.demo.pay.dto.WechatPrepayRequest;
import com.demo.pay.entity.OrderEntity;
import com.demo.pay.entity.PaymentEntity;
import com.demo.pay.exception.BusinessException;
import com.demo.pay.model.OrderSnapshot;
import com.demo.pay.repository.PaymentRepository;
import com.demo.pay.util.LogMaskUtil;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.wechat.pay.java.core.Config;
import com.wechat.pay.java.core.RSAAutoCertificateConfig;
import com.wechat.pay.java.core.notification.NotificationParser;
import com.wechat.pay.java.core.notification.RequestParam;
import com.wechat.pay.java.service.payments.h5.H5Service;
import com.wechat.pay.java.service.payments.model.Transaction;
import com.wechat.pay.java.service.payments.nativepay.NativePayService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class WechatPayService {

    private static final Logger log = LoggerFactory.getLogger(WechatPayService.class);
    private static final String TRADE_TYPE_NATIVE = "NATIVE";
    private static final String TRADE_TYPE_H5 = "H5";

    private final OrderService orderService;
    private final PaymentRepository paymentRepository;
    private final ObjectMapper objectMapper;
    private final PublicAccessProperties publicAccessProperties;
    private final WechatPayProperties wechatPayProperties;

    private volatile SdkClients sdkClients;

    public WechatPayService(OrderService orderService,
                            PaymentRepository paymentRepository,
                            ObjectMapper objectMapper,
                            PublicAccessProperties publicAccessProperties,
                            WechatPayProperties wechatPayProperties) {
        this.orderService = orderService;
        this.paymentRepository = paymentRepository;
        this.objectMapper = objectMapper;
        this.publicAccessProperties = publicAccessProperties;
        this.wechatPayProperties = wechatPayProperties;
    }

    @Transactional
    public Map<String, Object> createPrepay(WechatPrepayRequest request,
                                            String headerIdempotentKey,
                                            String clientIp,
                                            String userAgent) {
        OrderEntity order = orderService.requireOrder(request.getOrderId());
        OrderSnapshot snapshot = orderService.readSnapshot(order);
        int expectedAmount = snapshot.getPayableTotal();
        if (request.getAmount() != null && request.getAmount() != expectedAmount) {
            throw new IllegalArgumentException("prepay amount mismatch");
        }

        String tradeType = resolveTradeType(request.getTradeType(), userAgent);
        String idempotentKey = firstNonBlank(headerIdempotentKey, request.getIdempotentKey(), "prepay:" + order.getOrderId());
        String notifyUrl = resolveNotifyUrl();
        String expiresAt = OffsetDateTime.now().plus(wechatPayProperties.getOrderExpireMinutes(), ChronoUnit.MINUTES).toString();
        PaymentEntity payment = paymentRepository.findByOrderId(order.getOrderId()).orElseGet(PaymentEntity::new);
        Map<String, Object> upstream = TRADE_TYPE_H5.equals(tradeType)
                ? createH5Prepay(request, order, snapshot, notifyUrl, expiresAt, clientIp)
                : createNativePrepay(order, snapshot, notifyUrl, expiresAt);

        if (payment.getCreatedAt() == null) {
            payment.setCreatedAt(LocalDateTime.now());
            payment.setNotifyCount(0);
        }
        payment.setOrderId(order.getOrderId());
        payment.setTraceId(firstNonBlank(request.getTraceId(), order.getTraceId()));
        payment.setIdempotentKey(idempotentKey);
        payment.setPayerOpenid(request.getOpenid());
        payment.setTradeType(tradeType);
        payment.setAmountTotal(expectedAmount);
        payment.setAmountCurrency(defaultCurrency(snapshot.getCurrency()));
        payment.setAmountUnit(defaultAmountUnit(snapshot.getAmountUnit()));
        payment.setStatus("PREPAY_CREATED");
        payment.setCodeUrl((String) upstream.get("code_url"));
        payment.setH5Url((String) upstream.get("h5_url"));
        payment.setRawPrepayPayload(writeJson(upstream));
        payment.setUpdatedAt(LocalDateTime.now());
        paymentRepository.save(payment);

        order.setPaymentStatus("PREPAY_CREATED");
        order.setUpdatedAt(LocalDateTime.now());

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("order_id", order.getOrderId());
        result.put("trace_id", order.getTraceId());
        result.put("idempotent_key", idempotentKey);
        result.put("amount", expectedAmount);
        result.put("payable_total", expectedAmount);
        result.put("amount_currency", payment.getAmountCurrency());
        result.put("amount_unit", payment.getAmountUnit());
        result.put("payment_status", "PREPAY_CREATED");
        result.put("pay_status", "PREPAY_CREATED");
        result.put("trade_type", tradeType);
        result.put("code_url", payment.getCodeUrl());
        result.put("h5_url", payment.getH5Url());
        result.put("return_url", resolveReturnUrl(order, request));
        result.put("time_expire", expiresAt);
        log.info("wechat prepay created, orderId={}, tradeType={}, openid={}",
                order.getOrderId(), tradeType, LogMaskUtil.maskOpenId(request.getOpenid()));
        return result;
    }

    @Transactional
    public Map<String, Object> queryPaymentStatus(String orderId, boolean syncFromWechat) {
        OrderEntity order = orderService.requireOrder(orderId);
        PaymentEntity payment = paymentRepository.findByOrderId(orderId).orElse(null);
        if (syncFromWechat && payment != null && wechatPayProperties.isConfigured()) {
            syncTradeState(order, payment);
        }

        Map<String, Object> view = orderService.getOrderView(orderId);
        if (payment != null) {
            view.put("payment_trade_type", payment.getTradeType());
            view.put("payment_code_url", payment.getCodeUrl());
            view.put("payment_h5_url", payment.getH5Url());
        }
        view.put("wechat_pay_enabled", wechatPayProperties.isEnabled());
        view.put("wechat_pay_configured", wechatPayProperties.isConfigured());
        return view;
    }

    @Transactional
    public Map<String, String> handleNotifyCallback(String body,
                                                    String serial,
                                                    String timestamp,
                                                    String nonce,
                                                    String signature,
                                                    String signatureType) {
        if (!wechatPayProperties.isConfigured()) {
            throw new BusinessException(503, "WECHAT_PAY_NOT_CONFIGURED");
        }

        RequestParam requestParam = new RequestParam.Builder()
                .serialNumber(serial)
                .timestamp(timestamp)
                .nonce(nonce)
                .signature(signature)
                .signType(signatureType)
                .body(body)
                .build();

        Transaction transaction = requireSdkClients().notificationParser.parse(requestParam, Transaction.class);
        applyTransaction(transaction, body);
        Map<String, String> ack = new LinkedHashMap<>();
        ack.put("code", "SUCCESS");
        ack.put("message", "成功");
        return ack;
    }

    private Map<String, Object> createNativePrepay(OrderEntity order,
                                                   OrderSnapshot snapshot,
                                                   String notifyUrl,
                                                   String expiresAt) {
        com.wechat.pay.java.service.payments.nativepay.model.Amount amount =
                new com.wechat.pay.java.service.payments.nativepay.model.Amount();
        amount.setTotal(snapshot.getPayableTotal());
        amount.setCurrency(defaultCurrency(snapshot.getCurrency()));

        com.wechat.pay.java.service.payments.nativepay.model.PrepayRequest request =
                new com.wechat.pay.java.service.payments.nativepay.model.PrepayRequest();
        request.setAppid(wechatPayProperties.getAppId());
        request.setMchid(wechatPayProperties.getMerchantId());
        request.setDescription(buildDescription(order, snapshot));
        request.setOutTradeNo(order.getOrderId());
        request.setTimeExpire(expiresAt);
        request.setNotifyUrl(notifyUrl);
        request.setAttach(buildAttach(order));
        request.setAmount(amount);

        com.wechat.pay.java.service.payments.nativepay.model.PrepayResponse response =
                requireSdkClients().nativePayService.prepay(request);
        return Map.of("code_url", response.getCodeUrl());
    }

    private Map<String, Object> createH5Prepay(WechatPrepayRequest request,
                                               OrderEntity order,
                                               OrderSnapshot snapshot,
                                               String notifyUrl,
                                               String expiresAt,
                                               String clientIp) {
        com.wechat.pay.java.service.payments.h5.model.Amount amount =
                new com.wechat.pay.java.service.payments.h5.model.Amount();
        amount.setTotal(snapshot.getPayableTotal());
        amount.setCurrency(defaultCurrency(snapshot.getCurrency()));

        com.wechat.pay.java.service.payments.h5.model.H5Info h5Info =
                new com.wechat.pay.java.service.payments.h5.model.H5Info();
        h5Info.setType("Wap");
        h5Info.setAppName(firstNonBlank(request.getAppName(), wechatPayProperties.getH5AppName(), "AI Light Assistant"));
        h5Info.setAppUrl(firstNonBlank(request.getAppUrl(), wechatPayProperties.getH5AppUrl(),
                order.getAccessDomain(), publicAccessProperties.getAccessDomain(), "https://example.com"));

        com.wechat.pay.java.service.payments.h5.model.SceneInfo sceneInfo =
                new com.wechat.pay.java.service.payments.h5.model.SceneInfo();
        sceneInfo.setPayerClientIp(firstNonBlank(request.getPayerClientIp(), clientIp,
                wechatPayProperties.getDefaultPayerClientIp(), "127.0.0.1"));
        sceneInfo.setH5Info(h5Info);

        com.wechat.pay.java.service.payments.h5.model.PrepayRequest upstream =
                new com.wechat.pay.java.service.payments.h5.model.PrepayRequest();
        upstream.setAppid(wechatPayProperties.getAppId());
        upstream.setMchid(wechatPayProperties.getMerchantId());
        upstream.setDescription(buildDescription(order, snapshot));
        upstream.setOutTradeNo(order.getOrderId());
        upstream.setTimeExpire(expiresAt);
        upstream.setNotifyUrl(notifyUrl);
        upstream.setAttach(buildAttach(order));
        upstream.setAmount(amount);
        upstream.setSceneInfo(sceneInfo);

        com.wechat.pay.java.service.payments.h5.model.PrepayResponse response =
                requireSdkClients().h5Service.prepay(upstream);
        return Map.of("h5_url", response.getH5Url());
    }

    private void syncTradeState(OrderEntity order, PaymentEntity payment) {
        Transaction transaction;
        if (TRADE_TYPE_H5.equalsIgnoreCase(payment.getTradeType())) {
            com.wechat.pay.java.service.payments.h5.model.QueryOrderByOutTradeNoRequest request =
                    new com.wechat.pay.java.service.payments.h5.model.QueryOrderByOutTradeNoRequest();
            request.setMchid(wechatPayProperties.getMerchantId());
            request.setOutTradeNo(order.getOrderId());
            transaction = requireSdkClients().h5Service.queryOrderByOutTradeNo(request);
        } else {
            com.wechat.pay.java.service.payments.nativepay.model.QueryOrderByOutTradeNoRequest request =
                    new com.wechat.pay.java.service.payments.nativepay.model.QueryOrderByOutTradeNoRequest();
            request.setMchid(wechatPayProperties.getMerchantId());
            request.setOutTradeNo(order.getOrderId());
            transaction = requireSdkClients().nativePayService.queryOrderByOutTradeNo(request);
        }
        applyTransaction(transaction, transaction.toString());
    }

    private void applyTransaction(Transaction transaction, String rawPayload) {
        String orderId = transaction.getOutTradeNo();
        OrderEntity order = orderService.requireOrder(orderId);
        PaymentEntity payment = paymentRepository.findByOrderId(orderId).orElseGet(PaymentEntity::new);
        if (payment.getCreatedAt() == null) {
            payment.setCreatedAt(LocalDateTime.now());
            payment.setNotifyCount(0);
        }
        payment.setOrderId(orderId);
        payment.setTraceId(firstNonBlank(order.getTraceId(), payment.getTraceId()));
        payment.setTradeType(transaction.getTradeType() == null ? payment.getTradeType() : transaction.getTradeType().name());
        payment.setTransactionId(transaction.getTransactionId());
        payment.setPayerOpenid(transaction.getPayer() == null ? payment.getPayerOpenid() : transaction.getPayer().getOpenid());
        payment.setAmountCurrency(transaction.getAmount() == null ? defaultCurrency(order.getAmountCurrency())
                : firstNonBlank(transaction.getAmount().getCurrency(), order.getAmountCurrency(), "CNY"));
        payment.setAmountUnit(defaultAmountUnit(order.getAmountUnit()));
        payment.setAmountTotal(transaction.getAmount() == null ? order.getPayableTotal()
                : transaction.getAmount().getPayerTotal() == null ? transaction.getAmount().getTotal() : transaction.getAmount().getPayerTotal());
        payment.setRawNotifyPayload(rawPayload);
        payment.setNotifyCount((payment.getNotifyCount() == null ? 0 : payment.getNotifyCount()) + 1);
        payment.setUpdatedAt(LocalDateTime.now());

        String tradeState = transaction.getTradeState() == null ? "UNKNOWN" : transaction.getTradeState().name();
        if ("SUCCESS".equalsIgnoreCase(tradeState)) {
            payment.setStatus("SUCCESS");
            payment.setPaidAt(transaction.getSuccessTime() == null ? LocalDateTime.now()
                    : OffsetDateTime.parse(transaction.getSuccessTime()).toLocalDateTime());
            paymentRepository.save(payment);
            orderService.markOrderPaid(orderId, payment.getAmountTotal(), payment.getPaidAt());
            log.info("wechat paid, orderId={}, transactionId={}", orderId, LogMaskUtil.maskIdentifier(payment.getTransactionId()));
            return;
        }

        payment.setStatus(tradeState);
        paymentRepository.save(payment);
        order.setPaymentStatus(tradeState);
        order.setUpdatedAt(LocalDateTime.now());
    }

    private SdkClients requireSdkClients() {
        if (!wechatPayProperties.isConfigured()) {
            throw new BusinessException(503, "WECHAT_PAY_NOT_CONFIGURED");
        }
        if (sdkClients != null) {
            return sdkClients;
        }
        synchronized (this) {
            if (sdkClients == null) {
                Config config = new RSAAutoCertificateConfig.Builder()
                        .merchantId(wechatPayProperties.getMerchantId())
                        .merchantSerialNumber(wechatPayProperties.getMerchantSerialNumber())
                        .privateKeyFromPath(wechatPayProperties.getPrivateKeyPath())
                        .apiV3Key(wechatPayProperties.getApiV3Key())
                        .build();
                sdkClients = new SdkClients(
                        new NotificationParser((RSAAutoCertificateConfig) config),
                        new NativePayService.Builder().config(config).build(),
                        new H5Service.Builder().config(config).build()
                );
            }
            return sdkClients;
        }
    }

    private String resolveTradeType(String requestTradeType, String userAgent) {
        String normalized = requestTradeType == null ? "" : requestTradeType.trim().toUpperCase();
        if (TRADE_TYPE_H5.equals(normalized) || TRADE_TYPE_NATIVE.equals(normalized)) {
            return normalized;
        }
        String ua = userAgent == null ? "" : userAgent.toLowerCase();
        return ua.contains("android") || ua.contains("iphone") || ua.contains("mobile") ? TRADE_TYPE_H5 : TRADE_TYPE_NATIVE;
    }

    private String resolveNotifyUrl() {
        String configured = firstNonBlank(wechatPayProperties.getNotifyUrl());
        if (configured != null) {
            return configured;
        }
        String domain = firstNonBlank(publicAccessProperties.getAccessDomain());
        if (domain == null) {
            throw new BusinessException(503, "WECHAT_PAY_NOTIFY_URL_MISSING");
        }
        return domain + "/notify";
    }

    private String resolveReturnUrl(OrderEntity order, WechatPrepayRequest request) {
        String returnUrl = firstNonBlank(request.getReturnUrl());
        if (returnUrl != null) {
            return returnUrl;
        }
        String domain = firstNonBlank(order.getAccessDomain(), publicAccessProperties.getAccessDomain());
        return domain == null ? null : domain + "/payment/orders/" + order.getOrderId() + "/pay/success";
    }

    private String buildDescription(OrderEntity order, OrderSnapshot snapshot) {
        if (snapshot.getItems() != null && !snapshot.getItems().isEmpty()) {
            OrderSnapshot.ItemInfo item = snapshot.getItems().get(0);
            return "Lighting order " + firstNonBlank(item.getSelectedNewSku(), item.getSelectedOldSku(), order.getOrderId());
        }
        return "Lighting order " + order.getOrderId();
    }

    private String buildAttach(OrderEntity order) {
        return writeJson(Map.of("order_id", order.getOrderId(), "trace_id", firstNonBlank(order.getTraceId(), "")));
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("serialize payment payload failed", ex);
        }
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return null;
    }

    private String defaultCurrency(String currency) {
        return currency == null || currency.isBlank() ? "CNY" : currency.trim().toUpperCase();
    }

    private String defaultAmountUnit(String amountUnit) {
        return amountUnit == null || amountUnit.isBlank() ? "FEN" : amountUnit.trim().toUpperCase();
    }

    private record SdkClients(
            NotificationParser notificationParser,
            NativePayService nativePayService,
            H5Service h5Service
    ) {
    }
}
