package com.example.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.example.demo.entity.LampInfo;

public interface LampInfoRepository extends JpaRepository<LampInfo, String> {
}
