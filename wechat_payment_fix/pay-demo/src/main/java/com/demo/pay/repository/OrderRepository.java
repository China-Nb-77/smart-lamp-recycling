package com.demo.pay.repository;

import com.demo.pay.entity.OrderEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface OrderRepository extends JpaRepository<OrderEntity, Long> {

    Optional<OrderEntity> findByOrderId(String orderId);

    Optional<OrderEntity> findByWaybillId(String waybillId);

    Optional<OrderEntity> findByIdempotentKey(String key);
}
