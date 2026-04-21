from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from redis import Redis
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import OrderView, SessionState, TimelineEvent


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


class Base(DeclarativeBase):
    pass


class OrderRecord(Base):
    __tablename__ = "agent_orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    receiver_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    receiver_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    order_status: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(64), nullable=False)
    pay_status: Mapped[str] = mapped_column(String(64), nullable=False)
    payable_total: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_currency: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    paid_amount_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    waybill_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    waybill_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prepay_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_idempotent_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_trade_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_h5_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recycle_progress: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    shipment_progress: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    mock_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class EventRecord(Base):
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class SessionStore:
    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def ping(self) -> bool:
        return bool(self._redis.ping())

    def load(self, session_id: str) -> SessionState | None:
        raw = self._redis.get(self._key(session_id))
        if raw is None:
            return None
        return SessionState.model_validate_json(raw)

    def save(self, session: SessionState) -> None:
        self._redis.setex(
            self._key(session.session_id),
            self._ttl_seconds,
            session.model_dump_json(),
        )

    def _key(self, session_id: str) -> str:
        return f"agent:session:{session_id}"


class OrderRepository:
    def __init__(self, engine) -> None:
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def upsert(self, order: OrderView) -> OrderView:
        payload = order.model_dump()
        with self._session_factory() as db:
            record = db.get(OrderRecord, order.order_id) or OrderRecord(order_id=order.order_id, trace_id=order.trace_id, session_id=order.snapshot.get("session_id", ""), status=order.status, order_status=order.order_status, payment_status=order.payment_status, pay_status=order.pay_status, payable_total=order.payable_total, amount_currency=order.amount_currency, amount_unit=order.amount_unit, snapshot=order.snapshot)
            for key, value in payload.items():
                if hasattr(record, key):
                    if key in {"paid_at", "qr_expires_at", "payment_updated_at"}:
                        value = parse_datetime(value)
                    setattr(record, key, value)
            if not record.created_at:
                record.created_at = utc_now()
            record.updated_at = utc_now()
            db.add(record)
            db.commit()
            db.refresh(record)
            return self._to_model(record)

    def get(self, order_id: str) -> OrderView | None:
        with self._session_factory() as db:
            record = db.get(OrderRecord, order_id)
            if record is None:
                return None
            return self._to_model(record)

    def _to_model(self, record: OrderRecord) -> OrderView:
        payload = {
            "order_id": record.order_id,
            "trace_id": record.trace_id,
            "user_id": record.user_id,
            "contact_name": record.contact_name,
            "contact_phone": record.contact_phone,
            "address_region": record.address_region,
            "full_address": record.full_address,
            "receiver_longitude": record.receiver_longitude,
            "receiver_latitude": record.receiver_latitude,
            "location_source": record.location_source,
            "address_source": record.address_source,
            "access_domain": record.access_domain,
            "status": record.status,
            "order_status": record.order_status,
            "payment_status": record.payment_status,
            "pay_status": record.pay_status,
            "payable_total": record.payable_total,
            "amount_currency": record.amount_currency,
            "amount_unit": record.amount_unit,
            "snapshot": record.snapshot,
            "paid_amount_total": record.paid_amount_total,
            "paid_at": record.paid_at.isoformat().replace("+00:00", "Z") if record.paid_at else None,
            "qr_status": record.qr_status,
            "qr_expires_at": record.qr_expires_at.isoformat().replace("+00:00", "Z") if record.qr_expires_at else None,
            "waybill_id": record.waybill_id,
            "waybill_status": record.waybill_status,
            "prepay_id": record.prepay_id,
            "transaction_id": record.transaction_id,
            "payment_idempotent_key": record.payment_idempotent_key,
            "payment_trade_type": record.payment_trade_type,
            "payment_code_url": record.payment_code_url,
            "payment_h5_url": record.payment_h5_url,
            "payment_updated_at": record.payment_updated_at.isoformat().replace("+00:00", "Z")
            if record.payment_updated_at
            else None,
            "qr_token": record.qr_token,
            "recycle_progress": record.recycle_progress or [],
            "shipment_progress": record.shipment_progress or [],
            "mock_mode": record.mock_mode,
            "payment_mode": record.payment_mode,
            "requires_review": record.requires_review,
        }
        return OrderView.model_validate(payload)


class EventRepository:
    def __init__(self, engine) -> None:
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def record(
        self,
        *,
        request_id: str,
        event_type: str,
        payload: dict[str, Any],
        session_id: str | None = None,
        order_id: str | None = None,
    ) -> None:
        with self._session_factory() as db:
            db.add(
                EventRecord(
                    request_id=request_id,
                    session_id=session_id,
                    order_id=order_id,
                    event_type=event_type,
                    payload=payload,
                )
            )
            db.commit()

    def list_by_session(self, session_id: str) -> list[TimelineEvent]:
        with self._session_factory() as db:
            result = db.execute(
                select(EventRecord).where(EventRecord.session_id == session_id).order_by(EventRecord.id.asc())
            )
            rows = result.scalars().all()
            return [
                TimelineEvent(
                    id=row.id,
                    request_id=row.request_id,
                    event_type=row.event_type,
                    session_id=row.session_id,
                    order_id=row.order_id,
                    payload=row.payload,
                    created_at=row.created_at,
                )
                for row in rows
            ]


def create_redis_client(redis_url: str) -> Redis:
    if redis_url.startswith("fakeredis://"):
        from fakeredis import FakeRedis

        return FakeRedis(decode_responses=True)
    return Redis.from_url(redis_url, decode_responses=True)


def create_database_engine(database_url: str):
    return create_engine(database_url, future=True, pool_pre_ping=True)


def initialize_database(engine) -> None:
    Base.metadata.create_all(engine)
