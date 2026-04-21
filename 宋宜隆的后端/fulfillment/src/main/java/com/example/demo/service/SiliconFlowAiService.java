package com.example.demo.service;

import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import java.util.*;

@Service
public class SiliconFlowAiService {

    private final RestTemplate restTemplate = new RestTemplate();
    
    private final String apiKey = "sk-nrgqimsclnyncxhyjmemflxuswyimgummxagsjhzqsqhwshz";
    private final String baseUrl = "https://api.siliconflow.cn/v1";

    // 谢欣园的订单服务地址
    private final String ORDER_SERVICE_URL = "http://192.168.200.55:8080/api/create_order";

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

    private String callSiliconFlow(List<Map<String, String>> messages) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", "deepseek-ai/DeepSeek-V3");
        requestBody.put("messages", messages);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            String url = baseUrl + "/chat/completions";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                List<Map<String, Object>> choices = (List<Map<String, Object>>) response.getBody().get("choices");
                if (choices != null && !choices.isEmpty()) {
                    Map<String, Object> message = (Map<String, Object>) choices.get(0).get("message");
                    return (String) message.get("content");
                }
            }
            return "小灯暂时走神了，请稍后再试。";
        } catch (Exception e) {
            e.printStackTrace();
            return "AI服务暂时不可用，请稍后再试。";
        }
    }

    // 向量语义
    public List<Double> getEmbedding(String text) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", "BAAI/bge-large-zh-v1.5");
        requestBody.put("input", text);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            String url = baseUrl + "/embeddings";
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                List<Map<String, Object>> data = (List<Map<String, Object>>) response.getBody().get("data");
                if (data != null && !data.isEmpty()) {
                    return (List<Double>) data.get(0).get("embedding");
                }
            }
            return null;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public double cosineSimilarity(List<Double> v1, List<Double> v2) {
        if (v1 == null || v2 == null || v1.size() != v2.size()) return 0;
        double dot = 0, norm1 = 0, norm2 = 0;
        for (int i = 0; i < v1.size(); i++) {
            dot += v1.get(i) * v2.get(i);
            norm1 += v1.get(i) * v1.get(i);
            norm2 += v2.get(i) * v2.get(i);
        }
        return dot / (Math.sqrt(norm1) * Math.sqrt(norm2));
    }

    // ========== 工具调用（真实接口） ==========
    public String callTool(String toolName, Map<String, Object> params) {
        switch (toolName) {
            case "create_order":
                return createOrder(params);
            case "track_logistics":
                return trackLogistics(params);
            default:
                return "未知工具";
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
            ResponseEntity<Map> response = restTemplate.postForEntity(ORDER_SERVICE_URL, entity, Map.class);
            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return "订单创建成功，订单号：" + response.getBody().get("order_id");
            }
            return "订单创建失败，请稍后再试。";
        } catch (Exception e) {
            e.printStackTrace();
            return "订单服务暂时不可用，请稍后再试。";
        }
    }

    private String trackLogistics(Map<String, Object> params) {
        String waybillId = (String) params.get("waybill_id");
        String url = "http://192.168.200.51:8080/api/track?waybillId=" + waybillId;
        
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                List<Map<String, String>> events = (List<Map<String, String>>) response.getBody().get("events");
                if (events != null && !events.isEmpty()) {
                    return "运单 " + waybillId + " 当前状态：" + events.get(events.size() - 1).get("desc");
                }
                return "运单 " + waybillId + " 暂无轨迹信息。";
            }
            return "查询失败，请稍后再试。";
        } catch (Exception e) {
            e.printStackTrace();
            return "物流服务暂时不可用，请稍后再试。";
        }
    }
}