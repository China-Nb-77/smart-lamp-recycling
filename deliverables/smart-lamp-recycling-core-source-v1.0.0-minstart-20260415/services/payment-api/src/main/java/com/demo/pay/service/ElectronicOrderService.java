package com.demo.pay.service;

import com.demo.pay.dto.ElectronicOrderViewResponse;
import com.demo.pay.dto.GenerateQrResponse;
import com.demo.pay.dto.TrackResponse;
import com.demo.pay.entity.OrderEntity;
import com.demo.pay.model.OrderSnapshot;
import com.demo.pay.util.SecurityUtil;
import com.demo.pay.util.LogMaskUtil;
import com.demo.pay.util.ValidationUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class ElectronicOrderService {

    private static final Logger log = LoggerFactory.getLogger(ElectronicOrderService.class);

    private final OrderService orderService;
    private final QrCodeService qrCodeService;
    private final ReplayGuardService replayGuardService;

    public ElectronicOrderService(OrderService orderService,
                                  QrCodeService qrCodeService,
                                  ReplayGuardService replayGuardService) {
        this.orderService = orderService;
        this.qrCodeService = qrCodeService;
        this.replayGuardService = replayGuardService;
    }

    @Transactional
    public GenerateQrResponse generateQr(String orderId, String userPhone) {
        OrderEntity order = orderService.requireOrder(orderId);
        OrderSnapshot snapshot = orderService.readSnapshot(order);
        String ownerPhone = snapshot.getUser() == null ? null : snapshot.getUser().getPhone();
        ValidationUtil.requireTrue(ownerPhone != null && ownerPhone.equals(userPhone), 403, "ORDER_ACCESS_DENIED");

        GenerateQrResponse response = qrCodeService.createOrRefresh(order);
        log.info("generate_qr success, orderId={}, owner={}, qr={}",
                orderId,
                LogMaskUtil.maskPhone(ownerPhone),
                LogMaskUtil.maskQrContent(response.getQrContent()));
        return response;
    }

    public ElectronicOrderViewResponse viewOrder(String orderId,
                                                 String token,
                                                 String timestamp,
                                                 String nonce,
                                                 String signature) {
        ValidationUtil.requireNotBlank(token, "token");
        OrderEntity order = orderService.requireOrder(orderId);
        qrCodeService.validateToken(order, token);
        replayGuardService.validate(orderId, token, timestamp, nonce, signature);

        OrderSnapshot snapshot = orderService.readSnapshot(order);
        ElectronicOrderViewResponse response = new ElectronicOrderViewResponse();
        response.setTraceId(snapshot.getTraceId());
        response.setOrderId(order.getOrderId());
        response.setStatus(order.getStatus());
        response.setPayStatus(resolvePaymentStatus(order));
        response.setQrStatus(order.getQrStatus());

        ElectronicOrderViewResponse.CustomerInfo customerInfo = new ElectronicOrderViewResponse.CustomerInfo();
        customerInfo.setUserId(snapshot.getUser() == null ? null : snapshot.getUser().getUserId());
        customerInfo.setName(LogMaskUtil.maskName(snapshot.getUser() == null ? null : snapshot.getUser().getName()));
        customerInfo.setPhone(LogMaskUtil.maskPhone(snapshot.getUser() == null ? null : snapshot.getUser().getPhone()));
        customerInfo.setAddress(LogMaskUtil.maskAddress(snapshot.getAddress() == null ? null : snapshot.getAddress().getFullAddress()));
        customerInfo.setRegion(snapshot.getAddress() == null ? null : snapshot.getAddress().getRegion());
        customerInfo.setLongitude(snapshot.getAddress() == null ? null : snapshot.getAddress().getLongitude());
        customerInfo.setLatitude(snapshot.getAddress() == null ? null : snapshot.getAddress().getLatitude());
        customerInfo.setLocationSource(snapshot.getAddress() == null ? null : snapshot.getAddress().getLocationSource());
        customerInfo.setAddressSource(snapshot.getAddress() == null ? null : snapshot.getAddress().getAddressSource());
        response.setCustomerInfo(customerInfo);

        ElectronicOrderViewResponse.ProductInfo productInfo = new ElectronicOrderViewResponse.ProductInfo();
        productInfo.setItems(snapshot.getItems().stream().map(item -> {
            ElectronicOrderViewResponse.ItemInfo itemInfo = new ElectronicOrderViewResponse.ItemInfo();
            itemInfo.setSelectedOldSku(item.getSelectedOldSku());
            itemInfo.setSelectedNewSku(item.getSelectedNewSku());
            itemInfo.setQty(item.getQty());
            return itemInfo;
        }).toList());
        response.setProductInfo(productInfo);

        ElectronicOrderViewResponse.AmountInfo amountInfo = new ElectronicOrderViewResponse.AmountInfo();
        amountInfo.setPayableTotal(snapshot.getPayableTotal());
        amountInfo.setPaidAmountTotal(order.getPaidAmountTotal());
        amountInfo.setCurrency(snapshot.getCurrency());
        amountInfo.setAmountUnit(snapshot.getAmountUnit());
        response.setAmount(amountInfo);

        ElectronicOrderViewResponse.QrInfo qrInfo = new ElectronicOrderViewResponse.QrInfo();
        qrInfo.setContent(qrCodeService.buildOrderViewLink(order, token));
        qrInfo.setExpiresAt(order.getQrExpiresAt());
        qrInfo.setStatus(order.getQrStatus());
        response.setQr(qrInfo);

        ElectronicOrderViewResponse.WaybillInfo waybillInfo = new ElectronicOrderViewResponse.WaybillInfo();
        waybillInfo.setWaybillId(order.getWaybillId());
        waybillInfo.setStatus(order.getWaybillStatus());
        response.setWaybill(waybillInfo);

        response.setEvents(buildEvents(order));
        log.info("electronic_order_view success, orderId={}, token={}, nonce={}",
                orderId,
                LogMaskUtil.maskToken(token),
                LogMaskUtil.maskNonce(nonce));
        return response;
    }

    public ElectronicOrderViewResponse viewOrderPublic(String orderId, String token) {
        String timestamp = String.valueOf(Instant.now().getEpochSecond());
        String nonce = UUID.randomUUID().toString();
        String signature = SecurityUtil.buildReplaySignature(orderId, token, timestamp, nonce);
        return viewOrder(orderId, token, timestamp, nonce, signature);
    }

    public TrackResponse track(String orderId) {
        OrderEntity order = orderService.requireOrder(orderId);
        TrackResponse response = new TrackResponse();
        response.setEvents(buildEvents(order));
        return response;
    }

    private List<ElectronicOrderViewResponse.EventInfo> buildEvents(OrderEntity order) {
        List<ElectronicOrderViewResponse.EventInfo> events = new ArrayList<>();
        events.add(event(order.getCreatedAt(), "订单已创建"));
        if (order.getPaidAt() != null) {
            events.add(event(order.getPaidAt(), "支付成功"));
        }
        if (order.getWaybillId() != null) {
            events.add(event(order.getUpdatedAt(), "货单已生成"));
        }
        return events;
    }

    private ElectronicOrderViewResponse.EventInfo event(LocalDateTime time, String desc) {
        ElectronicOrderViewResponse.EventInfo eventInfo = new ElectronicOrderViewResponse.EventInfo();
        eventInfo.setTime(time == null ? null : time.toString());
        eventInfo.setDesc(desc);
        return eventInfo;
    }

    private String resolvePaymentStatus(OrderEntity order) {
        if (order.getPaymentStatus() != null && !order.getPaymentStatus().isBlank()) {
            return order.getPaymentStatus();
        }
        return "PAID".equals(order.getStatus()) ? "PAID" : "UNPAID";
    }
}
