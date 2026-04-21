package com.example.demo.service;

import com.example.demo.entity.ChatHistory;
import com.example.demo.repository.ChatHistoryRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ChatMemoryService {

    @Autowired
    private ChatHistoryRepository chatHistoryRepository;

    /**
     * 获取会话的对话记忆（最近 N 轮）
     */
    public List<Map<String, String>> getMemory(String sessionId, int maxTurns) {
        List<ChatHistory> history = chatHistoryRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
        
        int start = Math.max(0, history.size() - maxTurns);
        return history.subList(start, history.size()).stream()
            .map(record -> Map.of(
                "role", "user",
                "content", record.getUserQuestion()
            ))
            .collect(Collectors.toList());
    }

    /**
     * 添加一轮对话到记忆
     */
    public void addMemory(String sessionId, String userMessage, String aiMessage) {
        // 这里交给 QnAController 的 save 处理，本类只做读取封装
    }

    /**
     * 生成会话摘要（用于长上下文压缩）
     */
    public String generateSummary(String sessionId) {
        List<ChatHistory> history = chatHistoryRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
        if (history.isEmpty()) return "";
        
        StringBuilder sb = new StringBuilder();
        for (ChatHistory record : history) {
            sb.append("用户问：").append(record.getUserQuestion()).append("\n");
            sb.append("助手答：").append(record.getAiAnswer()).append("\n");
        }
        return sb.toString();
    }
}