# AI Lamp Type Recognition Module

This package contains the lamp type recognition module and the minimum integration files created in the current round.

## Included

- `image_quote_system/classification/`
- `image_quote_system/serving/lamp_type_api.py`
- `image_quote_system/serving/api.py`
- `image_quote_system/serving/agent_backend.py`
- `image_quote_system/cli.py`
- `image_quote_system/entrypoints.py`
- `scripts/serve_lamp_type_api.py`
- `src/modules/vision/components/RecycleQuoteCard.tsx`
- `src/types/vision.ts`
- `tests/test_lamp_type_api.py`
- `tests/test_agent_api.py`
- `pyproject.toml`

## Install

```powershell
pip install -e ".[classify]"
```

## Run Standalone API

```powershell
python -m image_quote_system.cli serve-lamp-type-api --host 127.0.0.1 --port 8090
```

## Integrated Test

The existing vision service now also supports:

- `POST /classify-lamp`
- `POST /classify-lamp-upload`

And enriches quote payloads with:

- `summary.lamp_type_label`
- `summary.lamp_type_score`
- `summary.lamp_type_backend`
- `summary.lamp_type_model_id`
