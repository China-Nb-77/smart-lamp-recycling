# Smart Lamp Recycling Full Core Source

Version: `v1.0.0`
Date: `2026-04-17`

## Included

- `frontend/`: React + Vite user frontend, admin frontend, auth, AI integration
- `services/fulfillment-api/`: Spring Boot fulfillment, admin, auth, recommend proxy
- `services/payment-api/`: Spring Boot payment and order service
- `services/vision-api/`: Python vision service, AI lamp type recognition, recommendation service
- `scripts/`: startup helpers

## Required Environment

- Java 17+
- Maven 3.9+
- Node.js 20+
- Python 3.11+
- Chrome or Edge

## Key Environment Variables

- `SILICONFLOW_API_KEY`
- `TAOBAO_BROWSER=edge`
- `TAOBAO_HEADLESS=false`
- `RECOMMEND_SERVICE_URL=http://127.0.0.1:8000/api/recommend`

## Start Order

1. `services/fulfillment-api`
2. `services/payment-api`
3. `services/vision-api`
4. `frontend`

## Default Local Ports

- `5173` frontend
- `8080` fulfillment API
- `8081` payment API
- `8000` vision API

## Notes

- Admin default account:
  - username: `admin`
  - password: `123456`
- AI image classify endpoint:
  - `POST /classify`
- Recommendation endpoint:
  - `POST /api/recommend`
