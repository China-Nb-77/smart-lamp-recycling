package com.example.demo.service;

import com.example.demo.entity.LampInfo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class VectorStoreService {

    @Autowired
    private SiliconFlowAiService aiService;

    // 向量存储（用内存 Map 模拟，生产环境换成 Redis/PGvector）
    private final Map<String, List<Double>> vectorStore = new ConcurrentHashMap<>();
    private final Map<String, LampInfo> metadataStore = new ConcurrentHashMap<>();

    /**
     * 添加文档到向量库
     */
    public void addDocument(String id, String text, LampInfo metadata) {
        List<Double> vector = aiService.getEmbedding(text);
        if (vector != null) {
            vectorStore.put(id, vector);
            metadataStore.put(id, metadata);
        }
    }

    /**
     * 删除文档
     */
    public void removeDocument(String id) {
        vectorStore.remove(id);
        metadataStore.remove(id);
    }

    /**
     * 根据问题检索最相似的文档
     */
    public List<LampInfo> search(String query, int topK) {
        List<Double> queryVector = aiService.getEmbedding(query);
        if (queryVector == null || vectorStore.isEmpty()) return Collections.emptyList();

        List<Map.Entry<String, List<Double>>> entries = new ArrayList<>(vectorStore.entrySet());
        entries.sort((a, b) -> {
            double scoreA = aiService.cosineSimilarity(queryVector, a.getValue());
            double scoreB = aiService.cosineSimilarity(queryVector, b.getValue());
            return Double.compare(scoreB, scoreA);
        });

        int limit = Math.min(topK, entries.size());
        List<LampInfo> results = new ArrayList<>();
        for (int i = 0; i < limit; i++) {
            String id = entries.get(i).getKey();
            LampInfo info = metadataStore.get(id);
            if (info != null) results.add(info);
        }
        return results;
    }
}