package com.example.demo.service;

import java.time.LocalDateTime;

import org.springframework.stereotype.Service;

import com.example.demo.entity.AdminUser;
import com.example.demo.repository.AdminUserRepository;

import jakarta.annotation.PostConstruct;

@Service
public class AdminBootstrapService {
    private final AdminUserRepository adminUserRepository;

    public AdminBootstrapService(AdminUserRepository adminUserRepository) {
        this.adminUserRepository = adminUserRepository;
    }

    @PostConstruct
    public void init() {
        if (adminUserRepository.findByUsername("admin").isPresent()) {
            return;
        }
        AdminUser user = new AdminUser();
        user.setUsername("admin");
        user.setPassword("123456");
        user.setRealName("超级管理员");
        user.setRole("super_admin");
        user.setStatus(1);
        user.setCreatedAt(LocalDateTime.now());
        adminUserRepository.save(user);
    }
}
