package com.demo.pay.service;

import com.demo.pay.config.PublicAccessProperties;
import com.demo.pay.dto.CreateOrderRequest;
import com.demo.pay.dto.GenerateQrResponse;
import com.demo.pay.entity.OrderEntity;
import com.demo.pay.entity.PaymentEntity;
import com.demo.pay.entity.OrderStatusLog;
import com.demo.pay.exception.BusinessException;
import com.demo.pay.model.OrderSnapshot;
import com.demo.pay.repository.OrderRepository;
import com.demo.pay.repository.OrderStatusLogRepository;
import com.demo.pay.repository.PaymentRepository;
import com.demo.pay.util.LogMaskUtil;
import com.demo.pay.util.ValidationUtil;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final OrderStatusLogRepository logRepository;
    private final PaymentRepository paymentRepository;
    private final ObjectMapper objectMapper;
    private final QrCodeService qrCodeService;
    private final PublicAccessProperties publicAccessProperties;

    public OrderService(OrderRepository orderRepository,
                        OrderStatusLogRepository logRepository,
                        PaymentRepository paymentRepository,
                        ObjectMapper objectMapper,
                        QrCodeService qrCodeService,
                        PublicAccessProperties publicAccessProperties) {
        this.orderRepository = orderRepository;
        this.logRepository = logRepository;
        this.paymentRepository = paymentRepository;
        this.objectMapper = objectMapper;
        this.qrCodeService = qrCodeService;
        this.publicAccessProperties = publicAccessProperties;
    }

    @Transactional
    public Map<String, Object> createOrder(CreateOrderRequest request, String idempotentKey) {
        validateCreateOrderRequest(request, idempotentKey);

        Optional<OrderEntity> existing = orderRepository.findByIdempotentKey(idempotentKey);
        if (existing.isPresent()) {
            return toOrderView(existing.get(), null);
        }

        OrderSnapshot snapshot = buildSnapshot(request);
        OrderEntity order = new OrderEntity();
        order.setOrderId(newOrderId());
        order.setTraceId(snapshot.getTraceId());
        order.setUserId(resolveUserId(request));
        order.setContactName(request.getUser() == null ? null : request.getUser().getName());
        order.setContactPhone(request.getUser() == null ? null : request.getUser().getPhone());
        order.setAddressRegion(request.getAddress() == null ? null : request.getAddress().getRegion());
        order.setFullAddress(request.getAddress() == null ? null : request.getAddress().getFullAddress());
        order.setReceiverLongitude(request.getAddress() == null ? null : request.getAddress().getLongitude());
        order.setReceiverLatitude(request.getAddress() == null ? null : request.getAddress().getLatitude());
        order.setLocationSource(request.getAddress() == null ? null : request.getAddress().getLocationSource());
        order.setAddressSource(request.getAddress() == null ? null : request.getAddress().getAddressSource());
        order.setAccessDomain(resolveAccessDomain(request.getAccessDomain()));
        order.setPayableTotal(snapshot.getPayableTotal());
        order.setAmountCurrency(defaultCurrency(request.getCurrency()));
        order.setAmountUnit(defaultAmountUnit(request.getAmountUnit()));
        order.setStatus("CREATED");
        order.setPaymentStatus("UNPAID");
        order.setIdempotentKey(idempotentKey);
        order.setSnapshotJson(writeSnapshot(snapshot));
        order.setCreatedAt(LocalDateTime.now());
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);

        GenerateQrResponse qrResponse = qrCodeService.createOrRefresh(order);
        orderRepository.save(order);

        log.info("create_order success, orderId={}, user={}, address={}, payableTotal={}",
                order.getOrderId(),
                LogMaskUtil.maskPhone(order.getContactPhone()),
                LogMaskUtil.maskAddress(snapshot.getAddress() == null ? null : snapshot.getAddress().getFullAddress()),
                snapshot.getPayableTotal());
        return toOrderView(order, qrResponse);
    }

    public Map<String, Object> getOrderView(String orderId) {
        return toOrderView(requireOrder(orderId), null);
    }

    public OrderEntity requireOrder(String orderId) {
        return orderRepository.findByOrderId(orderId)
                .orElseThrow(() -> new BusinessException(404, "ORDER_NOT_FOUND"));
    }

    public OrderSnapshot readSnapshot(OrderEntity order) {
        try {
            return objectMapper.readValue(order.getSnapshotJson(), OrderSnapshot.class);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("failed to parse order snapshot for " + order.getOrderId(), ex);
        }
    }

    @Transactional
    public boolean markOrderPaid(String orderId, int paidAmountFen, LocalDateTime paidAt) {
        OrderEntity order = requireOrder(orderId);
        OrderSnapshot snapshot = readSnapshot(order);
        int expectedAmount = ValidationUtil.requirePositive(snapshot.getPayableTotal(), "snapshot.payable_total");

        if (paidAmountFen != expectedAmount) {
            throw new IllegalArgumentException("notify amount mismatch, expected=" + expectedAmount + ", actual=" + paidAmountFen);
        }

        if ("PAID".equals(order.getStatus())) {
            return false;
        }

        String oldStatus = order.getStatus();
        order.setStatus("PAID");
        order.setPaymentStatus("PAID");
        order.setPaidAmountTotal(paidAmountFen);
        order.setPaidAt(paidAt == null ? LocalDateTime.now() : paidAt);
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);

        OrderStatusLog logEntity = new OrderStatusLog();
        logEntity.setOrderId(orderId);
        logEntity.setOldStatus(oldStatus);
        logEntity.setNewStatus("PAID");
        logEntity.setCreatedAt(LocalDateTime.now());
        logRepository.save(logEntity);
        return true;
    }

    public String resolveIdempotentKey(CreateOrderRequest request, String requestKey) {
        if (requestKey != null && !requestKey.isBlank()) {
            return requestKey;
        }
        if (request.getTraceId() != null && !request.getTraceId().isBlank()) {
            return "trace:" + request.getTraceId();
        }
        throw new IllegalArgumentException("missing idempotent key");
    }

    public Map<String, Object> toOrderView(OrderEntity order, GenerateQrResponse qrResponse) {
        OrderSnapshot snapshot = readSnapshot(order);
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("order_id", order.getOrderId());
        view.put("trace_id", order.getTraceId());
        view.put("user_id", order.getUserId());
        view.put("contact_name", LogMaskUtil.maskName(order.getContactName()));
        view.put("contact_phone", LogMaskUtil.maskPhone(order.getContactPhone()));
        view.put("address_region", order.getAddressRegion());
        view.put("full_address", LogMaskUtil.maskAddress(order.getFullAddress()));
        view.put("receiver_longitude", order.getReceiverLongitude());
        view.put("receiver_latitude", order.getReceiverLatitude());
        view.put("location_source", order.getLocationSource());
        view.put("address_source", order.getAddressSource());
        view.put("access_domain", order.getAccessDomain());
        view.put("status", order.getStatus());
        view.put("order_status", order.getStatus());
        view.put("payment_status", resolvePaymentStatus(order));
        view.put("pay_status", resolvePaymentStatus(order));
        view.put("payable_total", snapshot.getPayableTotal());
        view.put("amount_currency", order.getAmountCurrency());
        view.put("amount_unit", order.getAmountUnit());
        view.put("snapshot", objectMapper.convertValue(maskSnapshot(snapshot), new TypeReference<Map<String, Object>>() { }));
        view.put("paid_amount_total", order.getPaidAmountTotal());
        view.put("paid_at", order.getPaidAt());
        view.put("qr_status", order.getQrStatus());
        view.put("qr_expires_at", order.getQrExpiresAt());
        view.put("waybill_id", order.getWaybillId());
        view.put("waybill_status", order.getWaybillStatus());
        Optional<PaymentEntity> payment = paymentRepository.findByOrderId(order.getOrderId());
        payment.ifPresent(value -> {
            view.put("prepay_id", value.getPrepayId());
            view.put("transaction_id", value.getTransactionId());
            view.put("payment_idempotent_key", value.getIdempotentKey());
            view.put("payment_trade_type", value.getTradeType());
            view.put("payment_code_url", value.getCodeUrl());
            view.put("payment_h5_url", value.getH5Url());
            view.put("payment_updated_at", value.getUpdatedAt());
        });
        if (qrResponse != null) {
            view.put("qr", qrResponse);
        }
        return view;
    }

    private void validateCreateOrderRequest(CreateOrderRequest request, String idempotentKey) {
        ValidationUtil.requireNotBlank(idempotentKey, "idempotent_key");
        ValidationUtil.requirePositive(request.getPayableTotal(), "payable_total");
        ValidationUtil.requireTrue(request.getItems() != null && !request.getItems().isEmpty(), 400, "INVALID_REQUEST");
        if (request.getUser() != null) {
            ValidationUtil.requirePresentAndNotBlank(request.getUser().getName(), "user.name");
            ValidationUtil.requirePresentAndNotBlank(request.getUser().getPhone(), "user.phone");
            ValidationUtil.maxLength(request.getUser().getUserId(), 64, "user.user_id");
            ValidationUtil.maxLength(request.getUser().getName(), 64, "user.name");
            ValidationUtil.validatePhone(ValidationUtil.maxLength(request.getUser().getPhone(), 32, "user.phone"), "user.phone");
        }
        if (request.getAddress() != null) {
            ValidationUtil.requirePresentAndNotBlank(request.getAddress().getFullAddress(), "address.full_address");
            ValidationUtil.maxLength(request.getAddress().getFullAddress(), 256, "address.full_address");
            ValidationUtil.maxLength(request.getAddress().getRegion(), 64, "address.region");
            ValidationUtil.maxLength(request.getAddress().getProvince(), 64, "address.province");
            ValidationUtil.maxLength(request.getAddress().getCity(), 64, "address.city");
            ValidationUtil.maxLength(request.getAddress().getDistrict(), 64, "address.district");
            ValidationUtil.maxLength(request.getAddress().getStreet(), 128, "address.street");
            ValidationUtil.validatePostalCode(ValidationUtil.maxLength(request.getAddress().getPostalCode(), 32, "address.postal_code"), "address.postal_code");
            ValidationUtil.maxLength(request.getAddress().getLocationSource(), 32, "address.location_source");
            ValidationUtil.maxLength(request.getAddress().getAddressSource(), 32, "address.address_source");
            ValidationUtil.requireTrue((request.getAddress().getLongitude() == null) == (request.getAddress().getLatitude() == null), 400, "INVALID_REQUEST");
            ValidationUtil.validateLongitude(request.getAddress().getLongitude(), "address.longitude");
            ValidationUtil.validateLatitude(request.getAddress().getLatitude(), "address.latitude");
        }
        ValidationUtil.maxLength(request.getCurrency(), 16, "currency");
        ValidationUtil.maxLength(request.getAmountUnit(), 16, "amount_unit");
        ValidationUtil.maxLength(resolveAccessDomain(request.getAccessDomain()), 128, "access_domain");
    }

    private OrderSnapshot buildSnapshot(CreateOrderRequest request) {
        OrderSnapshot snapshot = new OrderSnapshot();
        snapshot.setTraceId(request.getTraceId());
        snapshot.setPayableTotal(ValidationUtil.requirePositive(request.getPayableTotal(), "payable_total"));
        snapshot.setCurrency(defaultCurrency(request.getCurrency()));
        snapshot.setAmountUnit(defaultAmountUnit(request.getAmountUnit()));
        snapshot.setAccessDomain(resolveAccessDomain(request.getAccessDomain()));

        if (request.getUser() != null) {
            OrderSnapshot.UserInfo user = new OrderSnapshot.UserInfo();
            user.setUserId(request.getUser().getUserId());
            user.setName(request.getUser().getName());
            user.setPhone(request.getUser().getPhone());
            snapshot.setUser(user);
        }

        if (request.getAddress() != null) {
            OrderSnapshot.AddressInfo address = new OrderSnapshot.AddressInfo();
            address.setFullAddress(request.getAddress().getFullAddress());
            address.setRegion(request.getAddress().getRegion());
            address.setProvince(request.getAddress().getProvince());
            address.setCity(request.getAddress().getCity());
            address.setDistrict(request.getAddress().getDistrict());
            address.setStreet(request.getAddress().getStreet());
            address.setPostalCode(request.getAddress().getPostalCode());
            address.setLongitude(request.getAddress().getLongitude());
            address.setLatitude(request.getAddress().getLatitude());
            address.setLocationSource(request.getAddress().getLocationSource());
            address.setAddressSource(request.getAddress().getAddressSource());
            snapshot.setAddress(address);
        }

        snapshot.setItems(request.getItems().stream().map(item -> {
            OrderSnapshot.ItemInfo snapshotItem = new OrderSnapshot.ItemInfo();
            snapshotItem.setSelectedOldSku(ValidationUtil.maxLength(item.getSelectedOldSku(), 64, "item.selected_old_sku"));
            snapshotItem.setSelectedNewSku(ValidationUtil.maxLength(item.getSelectedNewSku(), 64, "item.selected_new_sku"));
            snapshotItem.setQty(ValidationUtil.requirePositive(item.getQty(), "item.qty"));
            return snapshotItem;
        }).toList());
        return snapshot;
    }

    private String writeSnapshot(OrderSnapshot snapshot) {
        try {
            return objectMapper.writeValueAsString(snapshot);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("failed to serialize order snapshot", ex);
        }
    }

    private String newOrderId() {
        return "ORD" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"));
    }

    private String resolveUserId(CreateOrderRequest request) {
        if (request.getUser() == null) {
            return null;
        }
        if (request.getUser().getUserId() != null && !request.getUser().getUserId().isBlank()) {
            return request.getUser().getUserId();
        }
        return request.getUser().getPhone();
    }

    private String defaultCurrency(String currency) {
        return currency == null || currency.isBlank() ? "CNY" : currency.trim().toUpperCase();
    }

    private String defaultAmountUnit(String amountUnit) {
        return amountUnit == null || amountUnit.isBlank() ? "FEN" : amountUnit.trim().toUpperCase();
    }

    private String resolveAccessDomain(String requestAccessDomain) {
        if (requestAccessDomain != null && !requestAccessDomain.isBlank()) {
            return requestAccessDomain.trim();
        }
        if (publicAccessProperties.getAccessDomain() == null || publicAccessProperties.getAccessDomain().isBlank()) {
            return null;
        }
        return publicAccessProperties.getAccessDomain();
    }

    private String resolvePaymentStatus(OrderEntity order) {
        if (order.getPaymentStatus() != null && !order.getPaymentStatus().isBlank()) {
            return order.getPaymentStatus();
        }
        return "PAID".equals(order.getStatus()) ? "PAID" : "UNPAID";
    }

    private OrderSnapshot maskSnapshot(OrderSnapshot snapshot) {
        OrderSnapshot masked = new OrderSnapshot();
        masked.setTraceId(snapshot.getTraceId());
        masked.setPayableTotal(snapshot.getPayableTotal());
        masked.setCurrency(snapshot.getCurrency());
        masked.setAmountUnit(snapshot.getAmountUnit());
        masked.setAccessDomain(snapshot.getAccessDomain());
        masked.setItems(snapshot.getItems());

        if (snapshot.getUser() != null) {
            OrderSnapshot.UserInfo user = new OrderSnapshot.UserInfo();
            user.setUserId(snapshot.getUser().getUserId());
            user.setName(LogMaskUtil.maskName(snapshot.getUser().getName()));
            user.setPhone(LogMaskUtil.maskPhone(snapshot.getUser().getPhone()));
            masked.setUser(user);
        }

        if (snapshot.getAddress() != null) {
            OrderSnapshot.AddressInfo address = new OrderSnapshot.AddressInfo();
            address.setFullAddress(LogMaskUtil.maskAddress(snapshot.getAddress().getFullAddress()));
            address.setRegion(snapshot.getAddress().getRegion());
            address.setProvince(snapshot.getAddress().getProvince());
            address.setCity(snapshot.getAddress().getCity());
            address.setDistrict(snapshot.getAddress().getDistrict());
            address.setStreet(LogMaskUtil.maskAddress(snapshot.getAddress().getStreet()));
            address.setPostalCode(snapshot.getAddress().getPostalCode());
            address.setLongitude(snapshot.getAddress().getLongitude());
            address.setLatitude(snapshot.getAddress().getLatitude());
            address.setLocationSource(snapshot.getAddress().getLocationSource());
            address.setAddressSource(snapshot.getAddress().getAddressSource());
            masked.setAddress(address);
        }
        return masked;
    }
}
