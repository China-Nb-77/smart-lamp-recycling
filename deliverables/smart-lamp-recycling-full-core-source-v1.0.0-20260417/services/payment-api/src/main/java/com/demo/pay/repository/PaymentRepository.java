package com.demo.pay.repository;

import com.demo.pay.entity.PaymentEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface PaymentRepository extends JpaRepository<PaymentEntity, Long> {

    Optional<PaymentEntity> findByOrderId(String orderId);

    Optional<PaymentEntity> findByPrepayId(String prepayId);

    Optional<PaymentEntity> findByTransactionId(String transactionId);

    Optional<PaymentEntity> findByIdempotentKey(String idempotentKey);
}
