package com.example.demo.service;

import com.example.demo.entity.LampInfo;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.util.*;

@Service
public class LampVectorService {

    @Autowired
    private VectorStoreService vectorStore;

    private final List<LampInfo> lamps = new ArrayList<>();

    @PostConstruct
    public void init() {
        lamps.add(new LampInfo("SKU001", "智能台灯A", "智能调光，可调色温，适合阅读"));
        lamps.add(new LampInfo("SKU002", "护眼台灯B", "无频闪，光线柔和，适合长时间使用"));
        lamps.add(new LampInfo("SKU003", "复古台灯C", "复古设计，装饰性强，暖光"));

        for (LampInfo lamp : lamps) {
            String text = lamp.getName() + "，" + lamp.getDescription();
            vectorStore.addDocument(lamp.getSku(), text, lamp);
        }
    }

    public LampInfo findMostSimilarLamp(String question) {
        List<LampInfo> results = vectorStore.search(question, 1);
        return results.isEmpty() ? null : results.get(0);
    }

    public List<LampInfo> getAllLamps() {
        return new ArrayList<>(lamps);
    }

    public void addLamp(LampInfo lamp) {
        String text = lamp.getName() + "，" + lamp.getDescription();
        vectorStore.addDocument(lamp.getSku(), text, lamp);
        lamps.add(lamp);
    }

    public void removeLamp(String sku) {
        vectorStore.removeDocument(sku);
        lamps.removeIf(lamp -> lamp.getSku().equals(sku));
    }
}