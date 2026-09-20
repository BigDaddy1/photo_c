# PhotoColor API

PhotoColor is a Dockerised FastAPI service for uploading JPEG images, extracting a five-colour RGB palette, persisting image metadata in PostgreSQL, and exposing aggregate RGB statistics.

## Architecture

- **FastAPI** provides the HTTP API and automatically generated OpenAPI documentation.
- **Pydantic** defines request and response contracts.
- **PostgreSQL** persists image metadata and the calculated palette.
- A Docker **named volume** persists the original JPEG files.
- **ImageStorageService** isolates file operations from the API. The current implementation uses the local Docker volume; a future S3 implementation can use the same `save`, `load`, and `delete` contract.
- **Pillow** validates JPEG input and uses median-cut quantisation to extract the five dominant colours.

The application deliberately uses class-based API views. Every endpoint inherits `APIView`, declares its URL and methods, and is registered centrally in `app/api/__init__.py`. This follows the routing pattern used in the referenced `driver-performance` project while retaining FastAPI's response-model support.

## Run with Docker

Requirements: Docker Desktop (or Docker Engine with Compose).

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`, the interactive documentation at `http://localhost:8000/docs`, and the OpenAPI JSON at `http://localhost:8000/openapi.json`.

To stop the stack while keeping the database and images:

```bash
docker compose down
```

To remove all local service data as well:

```bash
docker compose down --volumes
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness check. |
| `POST` | `/images` | Upload one JPEG file via multipart field `file`. |
| `GET` | `/images` | List recent uploads, newest first. Supports `limit` (1–100) and `offset` (>=0). |
| `GET` | `/images/{image_id}` | Return metadata for one image. |
| `GET` | `/images/{image_id}/palette` | Return exactly five RGB hex colours. |
| `GET` | `/images/{image_id}/file` | Download the original JPEG. |
| `DELETE` | `/images/{image_id}` | Delete metadata and the stored JPEG. |
| `GET` | `/rgbstats` | Return `[red, green, blue]` integer percentages across stored palettes. |

### Upload and inspect an image

The service accepts a real JPEG by inspecting the file contents, not by trusting the filename or MIME header. The maximum upload size defaults to 10 MiB and can be changed with `MAX_UPLOAD_BYTES`.

```bash
curl -X POST http://localhost:8000/images \
  -F 'file=@./example.jpg;type=image/jpeg'
```

Example response (`201 Created`):

```json
{
  "id": "4d4cda05-5af5-48e2-8ab6-9f9e3b7af0cf",
  "original_filename": "example.jpg",
  "content_type": "image/jpeg",
  "width": 1920,
  "height": 1080,
  "created_at": "2026-09-14T11:45:00+00:00",
  "updated_at": "2026-09-14T11:45:00+00:00"
}
```

```bash
IMAGE_ID=4d4cda05-5af5-48e2-8ab6-9f9e3b7af0cf
curl http://localhost:8000/images/$IMAGE_ID/palette
curl http://localhost:8000/images?limit=20&offset=0
curl http://localhost:8000/images/$IMAGE_ID/file --output original.jpg
curl http://localhost:8000/rgbstats
curl -X DELETE -i http://localhost:8000/images/$IMAGE_ID
```

The palette response has this shape:

```json
["#d64545", "#f2c078", "#263859", "#e9e2d0", "#141414"]
```

`/rgbstats` reads a single aggregate row from PostgreSQL, then normalises its RGB totals using largest-remainder rounding so the integer result always sums to `100`. The aggregate is incremented during image creation and decremented during deletion in the same database transaction as the image record. This keeps the endpoint fast even when the image table grows. An empty database returns `[0, 0, 0]`.

### Error responses

- `404`: an image or stored file does not exist.
- `413`: upload exceeds `MAX_UPLOAD_BYTES`.
- `415`: uploaded content is not a valid JPEG.
- `422`: malformed multipart request or invalid query/path parameters.

## Test images supplied with the task

The five supplied clipboard images are PNG files. This is useful to confirm that the JPEG validation returns `415`, but they must be converted before testing a successful upload. On macOS:

```bash
sips -s format jpeg source.png --out source.jpg
curl -X POST http://localhost:8000/images -F 'file=@source.jpg;type=image/jpeg'
```

## Automated tests

Install the project and its development dependencies with a Python 3.12+ environment, then run:

```bash
pip install -e '.[dev]'
pytest
```

The included tests cover the global RGB calculation and its rounding invariant. The Docker smoke test described above covers the HTTP workflow against PostgreSQL.

## Console endpoint demo

With the Docker stack running, execute every endpoint and print each response to the console:

```bash
python3 scripts/demo_api.py
```

By default the script uploads `tests/fixtures/fez.jpg`. You may provide a different API URL and local JPEG path:

```bash
python3 scripts/demo_api.py http://localhost:8000 /path/to/photo.jpg
```

The script creates one image and removes that same image at the end, including when it exits early.

## Error logs

Unexpected server-side exceptions are logged with a traceback and the request method/path. The client receives a generic `500 Internal Server Error` response without internal implementation details. Expected client errors, such as an unsupported file type (`415`) or an unknown image (`404`), are not logged as application errors.

When using Docker Compose, inspect error output with:

```bash
docker compose logs api
```

## Persistence note

Alembic owns the database schema. The Docker API container runs `alembic upgrade head` before starting Uvicorn, so a fresh local database is initialised automatically and subsequent image versions can apply versioned migrations. In a multi-instance production deployment, migrations should instead run once as a separate CI/CD deployment step before rolling out application instances.
