package com.example.demo.controller;

import com.example.demo.service.SiliconFlowAiService;
import com.example.demo.service.LampVectorService;
import com.example.demo.service.ChatMemoryService;
import com.example.demo.repository.ChatHistoryRepository;
import com.example.demo.entity.ChatHistory;
import com.example.demo.entity.LampInfo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.PostConstruct;
import java.time.LocalDateTime;
import java.util.*;

@RestController
@RequestMapping("/api/qna")
public class QnAController {

    @Autowired
    private SiliconFlowAiService aiService;

    @Autowired
    private LampVectorService lampVectorService;

    @Autowired
    private ChatMemoryService chatMemoryService;

    @Autowired
    private ChatHistoryRepository chatHistoryRepository;

    @PostConstruct
    public void init() {
        lampVectorService.init();
    }

    @PostMapping("/ask")
    public Map<String, Object> ask(@RequestBody Map<String, Object> request) {
        String traceId = generateTraceId();
        String question = (String) request.get("question");
        String sessionId = (String) request.getOrDefault("session_id", "default");
        
        // ========== 多模态接入 ==========
        String imageUrl = (String) request.get("image_url");
        String recognizedSku = (String) request.get("recognized_sku");

        // ========== 意图识别与工具调用 ==========
        String intent = "";
        if (question.contains("下单") || question.contains("购买") || question.contains("我要买")) {
            intent = "create_order";
        } else if (question.contains("物流") || question.contains("查单") || question.contains("货到哪了")) {
            intent = "track_logistics";
        }

        String answer;
        if ("create_order".equals(intent)) {
            Map<String, Object> params = new HashMap<>();
            params.put("sku", "SKU001");
            params.put("qty", 1);
            params.put("address", "默认地址");
            answer = aiService.callTool("create_order", params);
        } else if ("track_logistics".equals(intent)) {
            Map<String, Object> params = new HashMap<>();
            params.put("waybill_id", "WB001");
            answer = aiService.callTool("track_logistics", params);
        } else {
            // ========== 语义搜索（RAG） ==========
            LampInfo matchedLamp = lampVectorService.findMostSimilarLamp(question);
            String context = "";
            
            // 优先使用图片识别结果
            if (recognizedSku != null && !recognizedSku.isEmpty()) {
                LampInfo recognized = lampVectorService.getAllLamps().stream()
                    .filter(l -> l.getSku().equals(recognizedSku))
                    .findFirst().orElse(null);
                if (recognized != null) {
                    context = "用户上传的图片识别结果是 " + recognized.getName() + "（SKU " + recognizedSku + "）。";
                }
            } else if (matchedLamp != null) {
                context = "用户可能对 " + matchedLamp.getName() + " 感兴趣。";
            }

            // ========== 历史记忆（使用 ChatMemoryService） ==========
            String historyContext = chatMemoryService.generateSummary(sessionId);
            if (!historyContext.isEmpty()) {
                historyContext = "历史对话：\n" + historyContext;
            }

            String systemPrompt = "你是灯具回收换新助手小灯。\n" + context + "\n" + historyContext + "\n回答要简洁友好，不超过100字。";
            answer = aiService.chatWithSystem(systemPrompt, question);
        }

        // ========== 存对话 ==========
        ChatHistory record = new ChatHistory();
        record.setSessionId(sessionId);
        record.setUserQuestion(question);
        record.setAiAnswer(answer);
        record.setTraceId(traceId);
        record.setCreatedAt(LocalDateTime.now());
        chatHistoryRepository.save(record);

        Map<String, Object> response = new HashMap<>();
        response.put("trace_id", traceId);
        response.put("answer", answer);
        response.put("session_id", sessionId);
        return response;
    }

    private String generateTraceId() {
        return "TRACE_" + UUID.randomUUID().toString().substring(0, 8);
    }
}