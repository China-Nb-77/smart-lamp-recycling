package com.demo.pay;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.time.Instant;
import java.util.UUID;

import static com.demo.pay.util.SecurityUtil.buildReplaySignature;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class PaymentFlowIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void fullPaymentChainShouldReachPaidAndAllowWaybill() throws Exception {
        MvcResult quoteResult = mockMvc.perform(post("/quote")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_001",
                                  "selected_old_sku": "OLD_001",
                                  "user_id": "user_001",
                                  "name": "zhangsan",
                                  "phone": "13800000000",
                                  "full_address": "Shanghai Pudong Test Rd 100",
                                  "region": "shanghai",
                                  "city": "Shanghai",
                                  "district": "Pudong",
                                  "longitude": 121.544,
                                  "latitude": 31.221,
                                  "location_source": "MANUAL_PIN",
                                  "address_source": "USER_INPUT",
                                  "qty": 2
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.payable_total").value(3980))
                .andExpect(jsonPath("$.data.options[0].new_sku").value("NEW-SKU-101"))
                .andExpect(jsonPath("$.data.identify.topk[0]").value("OLD_001"))
                .andExpect(jsonPath("$.data.need_more_info").value(false))
                .andExpect(jsonPath("$.data.ask").value(""))
                .andReturn();

        JsonNode quoteJson = objectMapper.readTree(quoteResult.getResponse().getContentAsString());
        int payableTotal = quoteJson.path("data").path("payable_total").asInt();

        MvcResult orderResult = mockMvc.perform(post("/create_order")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_001",
                                  "user": {"user_id": "user_001", "name": "zhangsan", "phone": "13800000000"},
                                  "address": {
                                    "full_address": "Shanghai Pudong Test Rd 100",
                                    "region": "shanghai",
                                    "city": "Shanghai",
                                    "district": "Pudong",
                                    "longitude": 121.544,
                                    "latitude": 31.221,
                                    "location_source": "MANUAL_PIN",
                                    "address_source": "USER_INPUT"
                                  },
                                  "items": [
                                    {
                                      "selected_old_sku": "OLD_001",
                                      "selected_new_sku": "NEW-SKU-101",
                                      "qty": 2
                                    }
                                  ],
                                  "payable_total": 3980,
                                  "currency": "CNY",
                                  "amount_unit": "FEN",
                                  "access_domain": "https://mvp.example.com"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.trace_id").value("tr_test_chain_001"))
                .andExpect(jsonPath("$.data.user_id").value("user_001"))
                .andExpect(jsonPath("$.data.contact_name").value("z*******"))
                .andExpect(jsonPath("$.data.contact_phone").value("138****0000"))
                .andExpect(jsonPath("$.data.full_address").value("Shangh****"))
                .andExpect(jsonPath("$.data.payment_status").value("UNPAID"))
                .andExpect(jsonPath("$.data.amount_currency").value("CNY"))
                .andExpect(jsonPath("$.data.amount_unit").value("FEN"))
                .andExpect(jsonPath("$.data.snapshot.payable_total").value(3980))
                .andExpect(jsonPath("$.data.snapshot.user.name").value("z*******"))
                .andExpect(jsonPath("$.data.snapshot.user.phone").value("138****0000"))
                .andExpect(jsonPath("$.data.snapshot.access_domain").value("https://mvp.example.com"))
                .andExpect(jsonPath("$.data.snapshot.address.longitude").value(121.544))
                .andExpect(jsonPath("$.data.snapshot.address.full_address").value("Shangh****"))
                .andExpect(jsonPath("$.data.qr.qr_content").exists())
                .andReturn();

        JsonNode orderJson = objectMapper.readTree(orderResult.getResponse().getContentAsString());
        String orderId = orderJson.path("data").path("order_id").asText();

        mockMvc.perform(get("/get_order").param("order_id", orderId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.contact_name").value("z*******"))
                .andExpect(jsonPath("$.data.contact_phone").value("138****0000"))
                .andExpect(jsonPath("$.data.full_address").value("Shangh****"))
                .andExpect(jsonPath("$.data.receiver_longitude").value(121.544))
                .andExpect(jsonPath("$.data.receiver_latitude").value(31.221));

        mockMvc.perform(post("/prepay")
                        .header("Idempotent-Key", "prepay-chain-001")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_001",
                                  "order_id": "%s",
                                  "amount": %d,
                                  "idempotent_key": "prepay-chain-001",
                                  "openid": "openid_demo_001"
                                }
                                """.formatted(orderId, payableTotal)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.amount").value(3980))
                .andExpect(jsonPath("$.data.payable_total").value(3980))
                .andExpect(jsonPath("$.data.payment_status").value("PREPAY_CREATED"))
                .andExpect(jsonPath("$.data.idempotent_key").value("prepay-chain-001"));

        mockMvc.perform(post("/notify")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_001",
                                  "out_trade_no": "%s",
                                  "transaction_id": "txn_test_001",
                                  "trade_state": "SUCCESS",
                                  "amount": {"total": %d, "currency": "CNY"},
                                  "success_time": "2026-03-12T10:00:00+08:00"
                                }
                                """.formatted(orderId, payableTotal)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.order_status").value("PAID"))
                .andExpect(jsonPath("$.data.payment_status").value("PAID"));

        mockMvc.perform(post("/create_waybill")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"order_id": "%s"}
                                """.formatted(orderId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.waybill_id").exists());

        MvcResult qrResult = mockMvc.perform(post("/api/v1/orders/{orderId}/qr", orderId)
                        .header("X-User-Phone", "13800000000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.qr_status").value("ACTIVE"))
                .andReturn();

        JsonNode qrJson = objectMapper.readTree(qrResult.getResponse().getContentAsString());
        String qrContent = qrJson.path("data").path("qr_content").asText();
        String token = qrContent.substring(qrContent.indexOf("token=") + 6);
        String timestamp = String.valueOf(Instant.now().getEpochSecond());
        String nonce = UUID.randomUUID().toString();
        String signature = buildReplaySignature(orderId, token, timestamp, nonce);

        mockMvc.perform(get("/api/v1/orders/{orderId}/view", orderId)
                        .param("token", token)
                        .header("X-Request-Timestamp", timestamp)
                        .header("X-Request-Nonce", nonce)
                        .header("X-Request-Signature", signature))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.order_id").value(orderId))
                .andExpect(jsonPath("$.data.customer_info.name").value("z*******"))
                .andExpect(jsonPath("$.data.customer_info.phone").value("138****0000"))
                .andExpect(jsonPath("$.data.customer_info.user_id").value("user_001"))
                .andExpect(jsonPath("$.data.customer_info.address").value("Shangh****"))
                .andExpect(jsonPath("$.data.customer_info.longitude").value(121.544))
                .andExpect(jsonPath("$.data.customer_info.latitude").value(31.221))
                .andExpect(jsonPath("$.data.amount.currency").value("CNY"))
                .andExpect(jsonPath("$.data.amount.amount_unit").value("FEN"))
                .andExpect(jsonPath("$.data.waybill.waybill_id").exists());

        mockMvc.perform(get("/track").param("order_id", orderId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.events").isArray());
    }

    @Test
    void duplicateNotifyShouldReturnSuccessWithoutRepeatingBusiness() throws Exception {
        MvcResult orderResult = mockMvc.perform(post("/create_order")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_002",
                                  "user": {"user_id": "user_002", "name": "lisi", "phone": "13900000000"},
                                  "address": {"full_address": "Shanghai Test Rd 200", "region": "shanghai"},
                                  "items": [
                                    {
                                      "selected_old_sku": "OLD_002",
                                      "selected_new_sku": "NEW-SKU-101",
                                      "qty": 1
                                    }
                                  ],
                                  "payable_total": 1990
                                }
                                """))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode orderJson = objectMapper.readTree(orderResult.getResponse().getContentAsString());
        String orderId = orderJson.path("data").path("order_id").asText();

        mockMvc.perform(post("/prepay")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "order_id": "%s",
                                  "amount": 1990,
                                  "idempotent_key": "prepay-chain-002",
                                  "openid": "openid_demo_002"
                                }
                                """.formatted(orderId)))
                .andExpect(status().isOk());

        String notifyBody = """
                {
                  "order_id": "%s",
                  "transaction_id": "txn_test_002",
                  "status": "SUCCESS",
                  "paid_amount_fen": 1990,
                  "paid_at": "2026-03-12T11:00:00+08:00"
                }
                """.formatted(orderId);

        mockMvc.perform(post("/notify")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(notifyBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.idempotent").value(false));

        mockMvc.perform(post("/notify")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(notifyBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.idempotent").value(true))
                .andExpect(jsonPath("$.data.order_status").value("PAID"))
                .andExpect(jsonPath("$.data.idempotent_key").value("prepay-chain-002"));
    }

    @Test
    void invalidTokenAndReplayShouldBeBlocked() throws Exception {
        MvcResult orderResult = mockMvc.perform(post("/create_order")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_003",
                                  "user": {"user_id": "user_003", "name": "wangwu", "phone": "13700000000"},
                                  "address": {"full_address": "Shanghai Test Rd 300", "region": "shanghai"},
                                  "items": [
                                    {
                                      "selected_old_sku": "OLD_003",
                                      "selected_new_sku": "NEW-SKU-101",
                                      "qty": 1
                                    }
                                  ],
                                  "payable_total": 1990
                                }
                                """))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode orderJson = objectMapper.readTree(orderResult.getResponse().getContentAsString());
        String orderId = orderJson.path("data").path("order_id").asText();

        MvcResult qrResult = mockMvc.perform(post("/api/v1/orders/{orderId}/qr", orderId)
                        .header("X-User-Phone", "13700000000"))
                .andExpect(status().isOk())
                .andReturn();

        JsonNode qrJson = objectMapper.readTree(qrResult.getResponse().getContentAsString());
        String qrContent = qrJson.path("data").path("qr_content").asText();
        String token = qrContent.substring(qrContent.indexOf("token=") + 6);

        String timestamp = String.valueOf(Instant.now().getEpochSecond());
        String nonce = UUID.randomUUID().toString();
        String signature = buildReplaySignature(orderId, token, timestamp, nonce);

        mockMvc.perform(get("/api/v1/orders/{orderId}/view", orderId)
                        .param("token", "bad-token")
                        .header("X-Request-Timestamp", timestamp)
                        .header("X-Request-Nonce", nonce)
                        .header("X-Request-Signature", signature))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("QR_TOKEN_INVALID"));

        mockMvc.perform(get("/api/v1/orders/{orderId}/view", orderId)
                        .param("token", token)
                        .header("X-Request-Timestamp", timestamp)
                        .header("X-Request-Nonce", nonce)
                        .header("X-Request-Signature", signature))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/v1/orders/{orderId}/view", orderId)
                        .param("token", token)
                        .header("X-Request-Timestamp", timestamp)
                        .header("X-Request-Nonce", nonce)
                        .header("X-Request-Signature", signature))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("QR_TOKEN_INVALID"));
    }
    @Test
    void publicOrderViewShouldBeReachableWithQrLink() throws Exception {
        MvcResult orderResult = mockMvc.perform(post("/create_order")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "trace_id": "tr_test_chain_004",
                                  "user": {"user_id": "user_004", "name": "zhaoliu", "phone": "13600000000"},
                                  "address": {"full_address": "Shanghai Test Rd 400", "region": "shanghai"},
                                  "items": [
                                    {
                                      "selected_old_sku": "OLD_004",
                                      "selected_new_sku": "NEW-SKU-101",
                                      "qty": 1
                                    }
                                  ],
                                  "payable_total": 1990
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.access_domain").value("http://localhost:8080"))
                .andExpect(jsonPath("$.data.qr.qr_content").value(Matchers.startsWith("http://localhost:8080/order-view?order_id=")))
                .andReturn();

        JsonNode orderJson = objectMapper.readTree(orderResult.getResponse().getContentAsString());
        String orderId = orderJson.path("data").path("order_id").asText();
        String qrContent = orderJson.path("data").path("qr").path("qr_content").asText();
        String token = qrContent.substring(qrContent.indexOf("token=") + 6);

        mockMvc.perform(get("/order-view")
                        .param("order_id", orderId)
                        .param("token", token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.order_id").value(orderId))
                .andExpect(jsonPath("$.data.customer_info.phone").value("136****0000"));
    }
}

