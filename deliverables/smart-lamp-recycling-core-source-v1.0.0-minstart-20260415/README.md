# Smart Lamp Recycling Core Source

Version: `v1.0.0`
Package date: `2026-04-15`
Package type: `minimal startup core source`

## Overview

This package keeps only the minimum source code required to build and start the core system:

- `frontend`: React + Vite web frontend
- `services/fulfillment-api`: Spring Boot fulfillment and Q&A service
- `services/payment-api`: Spring Boot payment and order service
- `services/vision-api`: Python vision and agent service
- `scripts`: unified Windows startup, stop, and frontend gateway scripts

The package intentionally excludes:

- mobile app source
- model weights and training artifacts
- experimental pipelines
- test code
- build output, logs, virtual environments, and local secrets

## Recommended Environment

- Windows Server 2022 or Windows 11
- Java 17+
- Maven 3.9+
- Node.js 20+
- npm 10+
- Python 3.11+

## Quick Start

Open PowerShell in the package root and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1
```

Stop all processes with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_windows.ps1
```

## Default Runtime Mode

The vision service starts in `mock` mode by default so the project can boot without heavy ML dependencies or model files.

If you want to enable a real vision pipeline later, update:

- `services/vision-api\requirements-runtime.txt`
- `services/vision-api\scripts\vision_local_server.py`

## Service Ports

- Frontend gateway: `5173`
- Fulfillment API: `8080`
- Payment API: `8081`
- Vision API: `8000`

## Notes

- The startup script will build frontend and Java services automatically if required.
- `services/fulfillment-api\src\main\resources\application.example.properties` is a template file without secrets.
- The frontend template config is stored in `frontend\.env.example`.
