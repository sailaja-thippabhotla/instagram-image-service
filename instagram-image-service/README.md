# Image Upload & Storage Service (API Gateway + Lambda + S3 + DynamoDB) — LocalStack Dev

This repo implements the coding exercise described in `Coding Exercise - Lead Platform Engineer.pdf`.

## What you get

APIs:

- `POST /images` — Upload image + metadata
- `GET  /images` — List images (supports filters: `user_id`, `tag`)
- `GET  /images/{image_id}` — Get a download URL (pre-signed URL)
- `DELETE /images/{image_id}` — Delete image + metadata

Backends:

- S3 for the image binary
- DynamoDB for metadata

Local dev:

- **LocalStack** runs S3 + DynamoDB locally
- **AWS SAM** runs API Gateway + Lambda locally (`sam local start-api`)

> Why SAM? It provides a faithful local API Gateway + Lambda execution model, while LocalStack provides the AWS services.

---

## Quick start (local)

### 1) Prereqs

- Docker + Docker Compose
- Python 3.7+
- AWS SAM CLI
- AWS CLI

### 2) Start LocalStack

```bash
docker compose up -d
```

LocalStack health: http://localhost:4566/_localstack/health

### 3) Create the bucket + table in LocalStack

```bash
python scripts/bootstrap_localstack.py
```

### 4) Run the API locally (API Gateway + Lambda)

```bash
python -m venv .venv
source .venv/bin/activate   # (Windows: .venv\Scripts\activate)

pip install -r requirements.txt

sam build
sam local start-api --port 3000
```

The API will be available at: http://127.0.0.1:3000

---

## API usage

### Upload image

**Request** (`POST /images`) JSON body:

```json
{
  "filename": "cat.png",
  "content_type": "image/png",
  "image_base64": "<BASE64_ENCODED_BYTES>",
  "user_id": "u-123",
  "tags": ["pets", "cats"],
  "metadata": {
    "caption": "my cat",
    "camera": "pixel"
  }
}
```

**Response**:

```json
{
  "image_id": "9a7d5b53-6c3c-4ad0-9a34-5f5d58e0a2c1",
  "created_at": "2026-02-22T00:00:00Z",
  "s3_key": "u-123/9a7d5b53-6c3c-4ad0-9a34-5f5d58e0a2c1/cat.png"
}
```

### List images

`GET /images?user_id=u-123&tag=cats`

- `user_id` filter uses a DynamoDB GSI (fast)
- `tag` filter uses a DynamoDB filter expression (contains)

### View / download

`GET /images/{image_id}` returns a **pre-signed download URL**:

```json
{
  "image_id": "...",
  "download_url": "http://localhost:4566/...signed...",
  "expires_in_seconds": 600
}
```

### Delete image

`DELETE /images/{image_id}`

---

## Tests

Unit tests use `pytest` + `moto` to mock S3 and DynamoDB.

```bash
pytest -q
```

---

## Notes / design choices

- Upload uses JSON with `image_base64` for simplicity in Lambda + API Gateway local emulation.
  In production you could switch to multipart uploads (API GW binary media types) or pre-signed PUT URLs.
- DynamoDB schema:
  - PK: `image_id` (string)
  - GSI1: `user_id` (PK) + `created_at` (SK) to list user images efficiently.
- Security/auth is out-of-scope for the exercise; `user_id` is accepted as a request field.

---

## Project layout

```
src/
  handlers.py
  services/
    repository.py
    storage.py
  util.py
tests/
scripts/
template.yaml
docker-compose.yml
```
