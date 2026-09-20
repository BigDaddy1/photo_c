"""Run every PhotoColor endpoint and print HTTP responses to the console."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IMAGE_PATH = PROJECT_ROOT / "tests/fixtures/fez.jpg"


def print_response(title: str, status: int, headers: Any, body: bytes) -> None:
    print(f"\n{'=' * 60}\n{title}\n--- Headers ---")
    print(f"HTTP {status}")
    for name, value in headers.items():
        print(f"{name}: {value}")
    print("\n--- Body ---")
    if not body:
        print("<empty body>")
        return
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(f"<binary data: {len(body)} bytes>")


def request(
    title: str,
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any, bytes]:
    try:
        with urlopen(Request(url, data=data, headers=headers or {}, method=method)) as response:
            body = response.read()
            print_response(title, response.status, response.headers, body)
            return response.status, response.headers, body
    except HTTPError as error:
        body = error.read()
        print_response(title, error.code, error.headers, body)
        raise RuntimeError(f"{method} {url} returned HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError(f"Could not connect to {url}: {error.reason}") from error


def encode_multipart_file(field_name: str, path: Path) -> tuple[bytes, str]:
    boundary = f"----PhotoColor{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode()
    body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", nargs="?", default="http://localhost:8000")
    parser.add_argument("image", nargs="?", type=Path, default=DEFAULT_IMAGE_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    image_path: Path = args.image
    if not image_path.is_file():
        print(f"JPEG file not found: {image_path}", file=sys.stderr)
        return 1

    print(f"PhotoColor endpoint demo\nBase URL: {base_url}\nJPEG: {image_path}")
    image_id: str | None = None

    try:
        request("GET /health", f"{base_url}/health")
        multipart, content_type = encode_multipart_file("file", image_path)
        _, _, upload_body = request(
            "POST /images",
            f"{base_url}/images",
            method="POST",
            data=multipart,
            headers={"Content-Type": content_type},
        )
        image_id = json.loads(upload_body)["id"]
        print(f"\nCreated image ID: {image_id}")

        request("GET /images?limit=20&offset=0", f"{base_url}/images?limit=20&offset=0")
        request(f"GET /images/{image_id}", f"{base_url}/images/{image_id}")
        request(f"GET /images/{image_id}/palette", f"{base_url}/images/{image_id}/palette")
        request("GET /rgbstats", f"{base_url}/rgbstats")

        _, _, downloaded_file = request(
            f"GET /images/{image_id}/file", f"{base_url}/images/{image_id}/file"
        )
        with tempfile.NamedTemporaryFile(prefix="photocolor-download-", suffix=".jpg", delete=False) as file:
            file.write(downloaded_file)
            downloaded_path = Path(file.name)
        print(f"Downloaded JPEG saved to: {downloaded_path} ({len(downloaded_file)} bytes)")

        request(f"DELETE /images/{image_id}", f"{base_url}/images/{image_id}", method="DELETE")
        image_id = None
        request("GET /rgbstats (after deletion)", f"{base_url}/rgbstats")
        print("\nDemo completed successfully.")
        return 0
    finally:
        if image_id is not None:
            try:
                request(
                    f"Cleanup DELETE /images/{image_id}",
                    f"{base_url}/images/{image_id}",
                    method="DELETE",
                )
            except RuntimeError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
