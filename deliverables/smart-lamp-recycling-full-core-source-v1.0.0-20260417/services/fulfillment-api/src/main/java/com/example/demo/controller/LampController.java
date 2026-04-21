package com.example.demo.controller;

import com.example.demo.entity.LampInfo;
import com.example.demo.service.LampVectorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/lamp")
public class LampController {

    @Autowired
    private LampVectorService lampVectorService;

    @GetMapping("/list")
    public List<LampInfo> getAllLamps() {
        return lampVectorService.getAllLamps();
    }

    @PostMapping("/add")
    public Map<String, Object> addLamp(@RequestBody LampInfo lamp) {
        lampVectorService.addLamp(lamp);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "success");
        response.put("message", "灯具已添加，向量已更新");
        return response;
    }

    @DeleteMapping("/{sku}")
    public Map<String, Object> removeLamp(@PathVariable String sku) {
        lampVectorService.removeLamp(sku);
        Map<String, Object> response = new HashMap<>();
        response.put("status", "success");
        response.put("message", "灯具已删除");
        return response;
    }

    @PostMapping("/search")
    public Map<String, Object> search(@RequestBody Map<String, String> request) {
        String question = request.get("question");
        LampInfo matched = lampVectorService.findMostSimilarLamp(question);
        Map<String, Object> response = new HashMap<>();
        if (matched != null) {
            response.put("sku", matched.getSku());
            response.put("name", matched.getName());
            response.put("description", matched.getDescription());
        }
        return response;
    }
}