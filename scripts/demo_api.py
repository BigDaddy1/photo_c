"""Run every PhotoColor endpoint and print HTTP responses to the console."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import tempfile
import uuid
from collections.abc import Collection
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
    expected_statuses: Collection[int] = (200,),
) -> tuple[int, Any, bytes]:
    try:
        with urlopen(Request(url, data=data, headers=headers or {}, method=method)) as response:
            body = response.read()
            print_response(title, response.status, response.headers, body)
            status, response_headers = response.status, response.headers
    except HTTPError as error:
        body = error.read()
        print_response(title, error.code, error.headers, body)
        status, response_headers = error.code, error.headers
    except URLError as error:
        raise RuntimeError(f"Could not connect to {url}: {error.reason}") from error

    if status not in expected_statuses:
        expected = ", ".join(map(str, expected_statuses))
        raise RuntimeError(f"{method} {url} returned HTTP {status}; expected one of: {expected}")
    print(f"\nResult: expected HTTP {status}")
    return status, response_headers, body


def encode_multipart_content(
    field_name: str,
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> tuple[bytes, str]:
    boundary = f"----PhotoColor{uuid.uuid4().hex}"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode()
    body = prefix + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def encode_multipart_file(field_name: str, path: Path) -> tuple[bytes, str]:
    return encode_multipart_content(
        field_name,
        filename=path.name,
        content=path.read_bytes(),
        content_type=mimetypes.guess_type(path.name)[0] or "image/jpeg",
    )


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

    print(f"PhotoColor endpoint smoke test\nBase URL: {base_url}\nJPEG: {image_path}")
    image_id: str | None = None
    missing_image_id = uuid.uuid4()

    try:
        request("GET /health — success", f"{base_url}/health")
        request(
            "POST /health — unsupported method",
            f"{base_url}/health",
            method="POST",
            expected_statuses=(405,),
        )

        invalid_multipart, invalid_content_type = encode_multipart_content(
            "file",
            filename="not-a-jpeg.txt",
            content=b"This is deliberately not a JPEG file.",
            content_type="text/plain",
        )
        request(
            "POST /images — invalid JPEG",
            f"{base_url}/images",
            method="POST",
            data=invalid_multipart,
            headers={"Content-Type": invalid_content_type},
            expected_statuses=(415,),
        )

        multipart, content_type = encode_multipart_file("file", image_path)
        _, _, upload_body = request(
            "POST /images — success",
            f"{base_url}/images",
            method="POST",
            data=multipart,
            headers={"Content-Type": content_type},
            expected_statuses=(201,),
        )
        image_id = json.loads(upload_body)["id"]
        print(f"\nCreated image ID: {image_id}")

        request("GET /images — success", f"{base_url}/images?limit=20&offset=0")
        request(
            "GET /images — invalid limit",
            f"{base_url}/images?limit=0&offset=0",
            expected_statuses=(422,),
        )

        request(f"GET /images/{image_id} — success", f"{base_url}/images/{image_id}")
        request(
            f"GET /images/{missing_image_id} — not found",
            f"{base_url}/images/{missing_image_id}",
            expected_statuses=(404,),
        )

        request(f"GET /images/{image_id}/palette — success", f"{base_url}/images/{image_id}/palette")
        request(
            f"GET /images/{missing_image_id}/palette — not found",
            f"{base_url}/images/{missing_image_id}/palette",
            expected_statuses=(404,),
        )

        request("GET /rgbstats — success", f"{base_url}/rgbstats")
        request(
            "POST /rgbstats — unsupported method",
            f"{base_url}/rgbstats",
            method="POST",
            expected_statuses=(405,),
        )

        _, _, downloaded_file = request(
            f"GET /images/{image_id}/file — success",
            f"{base_url}/images/{image_id}/file",
        )
        if downloaded_file != image_path.read_bytes():
            raise RuntimeError("Downloaded JPEG does not match the uploaded file")
        print("Downloaded JPEG matches the uploaded file byte-for-byte.")
        with tempfile.NamedTemporaryFile(prefix="photocolor-download-", suffix=".jpg", delete=False) as file:
            file.write(downloaded_file)
            downloaded_path = Path(file.name)
        print(f"Downloaded JPEG saved to: {downloaded_path} ({len(downloaded_file)} bytes)")

        request(
            f"GET /images/{missing_image_id}/file — not found",
            f"{base_url}/images/{missing_image_id}/file",
            expected_statuses=(404,),
        )

        request(
            f"DELETE /images/{image_id} — success",
            f"{base_url}/images/{image_id}",
            method="DELETE",
            expected_statuses=(204,),
        )
        image_id = None
        request(
            f"DELETE /images/{missing_image_id} — not found",
            f"{base_url}/images/{missing_image_id}",
            method="DELETE",
            expected_statuses=(404,),
        )
        request("GET /rgbstats — after deletion", f"{base_url}/rgbstats")
        print("\nAll smoke-test cases completed successfully.")
        return 0
    finally:
        if image_id is not None:
            try:
                request(
                    f"Cleanup DELETE /images/{image_id}",
                    f"{base_url}/images/{image_id}",
                    method="DELETE",
                    expected_statuses=(204, 404),
                )
            except RuntimeError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
