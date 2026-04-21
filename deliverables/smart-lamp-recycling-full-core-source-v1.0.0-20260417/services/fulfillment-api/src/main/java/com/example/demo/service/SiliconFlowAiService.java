package com.example.demo.service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class SiliconFlowAiService {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${siliconflow.api-key:${SILICONFLOW_API_KEY:}}")
    private String apiKey;

    @Value("${siliconflow.base-url:${SILICONFLOW_BASE_URL:https://api.siliconflow.cn/v1}}")
    private String baseUrl;

    @Value("${siliconflow.chat-model:${SILICONFLOW_CHAT_MODEL:deepseek-ai/DeepSeek-V3}}")
    private String chatModel;

    @Value("${siliconflow.embedding-model:${SILICONFLOW_EMBEDDING_MODEL:BAAI/bge-large-zh-v1.5}}")
    private String embeddingModel;

    @Value("${tool.order-service-url:${ORDER_SERVICE_URL:http://127.0.0.1:8081/create_order}}")
    private String orderServiceUrl;

    @Value("${tool.track-service-url-template:${TRACK_SERVICE_URL_TEMPLATE:http://127.0.0.1:8081/track?order_id=%s}}")
    private String trackServiceUrlTemplate;

    public String chat(String userMessage) {
        return callSiliconFlow(List.of(
            Map.of("role", "user", "content", userMessage)
        ));
    }

    public String chatWithSystem(String systemPrompt, String userMessage) {
        return callSiliconFlow(List.of(
            Map.of("role", "system", "content", systemPrompt),
            Map.of("role", "user", "content", userMessage)
        ));
    }

    public List<Double> getEmbedding(String text) {
        if (apiKey == null || apiKey.isBlank()) {
            return null;
        }

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", embeddingModel);
        requestBody.put("input", text);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey.trim());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            String url = baseUrl + "/embeddings";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                return null;
            }

            Object dataObj = response.getBody().get("data");
            if (!(dataObj instanceof List<?> data) || data.isEmpty()) {
                return null;
            }

            Object item = data.get(0);
            if (!(item instanceof Map<?, ?> itemMap)) {
                return null;
            }

            Object embedding = itemMap.get("embedding");
            if (embedding instanceof List<?> vector) {
                @SuppressWarnings("unchecked")
                List<Double> casted = (List<Double>) vector;
                return casted;
            }
            return null;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public double cosineSimilarity(List<Double> v1, List<Double> v2) {
        if (v1 == null || v2 == null || v1.size() != v2.size()) {
            return 0;
        }
        double dot = 0;
        double norm1 = 0;
        double norm2 = 0;
        for (int i = 0; i < v1.size(); i++) {
            dot += v1.get(i) * v2.get(i);
            norm1 += v1.get(i) * v1.get(i);
            norm2 += v2.get(i) * v2.get(i);
        }
        return dot / (Math.sqrt(norm1) * Math.sqrt(norm2));
    }

    public String callTool(String toolName, Map<String, Object> params) {
        switch (toolName) {
            case "create_order":
                return createOrder(params);
            case "track_logistics":
                return trackLogistics(params);
            default:
                return "Unknown tool";
        }
    }

    private String callSiliconFlow(List<Map<String, String>> messages) {
        if (apiKey == null || apiKey.isBlank()) {
            return "AI service is not configured. Please set SILICONFLOW_API_KEY.";
        }

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", chatModel);
        requestBody.put("messages", messages);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey.trim());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            String url = baseUrl + "/chat/completions";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                return "AI service is temporarily unavailable.";
            }

            Object choicesObj = response.getBody().get("choices");
            if (!(choicesObj instanceof List<?> choices) || choices.isEmpty()) {
                return "AI service is temporarily unavailable.";
            }

            Object firstChoice = choices.get(0);
            if (!(firstChoice instanceof Map<?, ?> choiceMap)) {
                return "AI service is temporarily unavailable.";
            }

            Object messageObj = choiceMap.get("message");
            if (!(messageObj instanceof Map<?, ?> messageMap)) {
                return "AI service is temporarily unavailable.";
            }

            Object contentObj = messageMap.get("content");
            if (contentObj instanceof String content && !content.isBlank()) {
                return content;
            }

            return "AI service returned an empty answer.";
        } catch (Exception e) {
            e.printStackTrace();
            return "AI service is temporarily unavailable.";
        }
    }

    private String createOrder(Map<String, Object> params) {
        String sku = (String) params.get("sku");
        Integer qty = (Integer) params.get("qty");
        String address = (String) params.get("address");

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("sku", sku);
        requestBody.put("qty", qty);
        requestBody.put("address", address);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(orderServiceUrl, entity, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                return "Order service is temporarily unavailable.";
            }

            Map<String, Object> body = response.getBody();
            Object orderId = extractValue(body, "order_id");
            if (orderId == null) {
                return "Order service did not return order_id.";
            }
            return "Order created: " + orderId;
        } catch (Exception e) {
            e.printStackTrace();
            return "Order service is temporarily unavailable.";
        }
    }

    private String trackLogistics(Map<String, Object> params) {
        String waybillId = (String) params.get("waybill_id");
        String url = String.format(
            trackServiceUrlTemplate,
            URLEncoder.encode(String.valueOf(waybillId == null ? "" : waybillId), StandardCharsets.UTF_8)
        );

        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                return "Tracking service is temporarily unavailable.";
            }

            Map<String, Object> body = response.getBody();
            Object eventsObj = extractValue(body, "events");
            if (!(eventsObj instanceof List<?> events) || events.isEmpty()) {
                return "No tracking updates yet.";
            }

            Object last = events.get(events.size() - 1);
            if (!(last instanceof Map<?, ?> lastEvent)) {
                return "Tracking format is invalid.";
            }

            Object desc = lastEvent.get("desc");
            if (desc == null) {
                desc = lastEvent.get("status");
            }

            return "Current tracking status: " + String.valueOf(desc == null ? "unknown" : desc);
        } catch (Exception e) {
            e.printStackTrace();
            return "Tracking service is temporarily unavailable.";
        }
    }

    private Object extractValue(Map<String, Object> body, String key) {
        if (body.containsKey(key)) {
            return body.get(key);
        }
        Object data = body.get("data");
        if (data instanceof Map<?, ?> dataMap) {
            return dataMap.get(key);
        }
        return null;
    }
}
