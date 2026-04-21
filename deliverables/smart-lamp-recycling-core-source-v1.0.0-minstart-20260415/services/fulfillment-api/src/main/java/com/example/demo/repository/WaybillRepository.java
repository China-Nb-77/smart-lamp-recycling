package com.example.demo.repository;

import com.example.demo.entity.Waybill;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface WaybillRepository extends JpaRepository<Waybill, Long> {
    Optional<Waybill> findByWaybillId(String waybillId);
    Optional<Waybill> findByOrderId(String orderId);
}
