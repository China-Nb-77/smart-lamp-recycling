# Upload API

## Endpoint

`POST /api/v1/files/upload`

Alternative alias:

`POST /files/upload`

## Request

- Content-Type: `multipart/form-data`
- Field name: `file`
- Allowed types: `image/jpeg`, `image/png`, `image/webp`
- Max file size: `10 MB`

## Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "success": true,
    "file_key": "randomkey",
    "original_name": "lamp-demo.jpg",
    "stored_name": "randomkey.jpg",
    "content_type": "image/jpeg",
    "file_size": 12345,
    "relative_path": "2026-04-01/randomkey.jpg",
    "public_url": "https://your-domain/uploads/2026-04-01/randomkey.jpg",
    "uploaded_at": "2026-04-01T00:00:00"
  }
}
```

## Static access

`GET /uploads/{date}/{storedName}`

## Config

- `app.upload.storage-dir`
- `app.upload.public-path`
- `app.public-access.access-domain`
