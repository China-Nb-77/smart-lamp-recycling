# Database Changes

## orders

Required fields for this patch:
- id: bigint primary key
- order_id: varchar unique not null
- trace_id: varchar null
- user_id: varchar null
- contact_name: varchar null
- contact_phone: varchar null
- address_region: varchar null
- full_address: varchar null
- receiver_longitude: decimal null
- receiver_latitude: decimal null
- location_source: varchar null
- address_source: varchar null
- access_domain: varchar null
- payable_total: int not null
- amount_currency: varchar not null default 'CNY'
- amount_unit: varchar not null default 'FEN'
- status: varchar not null
- payment_status: varchar not null default 'UNPAID'
- idempotent_key: varchar unique null
- snapshot_json: text not null
- paid_amount_total: int null
- paid_at: datetime null
- qr_token_hash: varchar null
- qr_expires_at: datetime null
- qr_status: varchar null
- waybill_id: varchar null
- waybill_status: varchar null
- created_at: datetime not null
- updated_at: datetime not null

Business truth field:
- orders.status
- orders.payment_status

## payments

New table introduced by this patch:
- id: bigint primary key
- order_id: varchar unique not null
- trace_id: varchar null
- prepay_id: varchar unique null
- transaction_id: varchar unique null
- idempotent_key: varchar unique null
- payer_openid: varchar null
- amount_total: int not null
- amount_currency: varchar not null default 'CNY'
- amount_unit: varchar not null default 'FEN'
- status: varchar not null
- raw_notify_payload: text null
- notify_count: int not null default 0
- paid_at: datetime null
- created_at: datetime not null
- updated_at: datetime not null

## snapshot

This patch stores order snapshot in orders.snapshot_json.
Required keys inside snapshot JSON:
- trace_id
- user
- address
- items
- payable_total
- currency
- amount_unit
- access_domain

Recommended nested keys for future compatibility:
- user.user_id
- user.name
- user.phone
- address.full_address
- address.region
- address.province
- address.city
- address.district
- address.street
- address.postal_code
- address.longitude
- address.latitude
- address.location_source
- address.address_source

## collection and masking

Current minimal backend behavior:
- create_order accepts name, phone, full_address, region, province, city, district, street, postal_code, longitude, latitude, location_source, address_source, user_id
- quote accepts the same collection fields as optional context for forward compatibility
- order query and electronic order view return masked name / phone / address
- longitude / latitude require paired input and valid ranges

## electronic order and QR

Electronic order query depends on:
- orders.order_id
- orders.trace_id
- orders.status
- orders.payment_status
- orders.qr_token_hash
- orders.qr_expires_at
- orders.qr_status
- orders.waybill_id
- orders.waybill_status
- orders.access_domain

Prepay / notify query depends on:
- payments.prepay_id
- payments.transaction_id
- payments.idempotent_key
