"""
Google Drive service — file listing, streaming, and synchronization.

Uses the official Google Drive API v3 via a service account.
The service account JSON is stored in the GOOGLE_SERVICE_ACCOUNT env var.
"""
import json
from typing import Generator

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import settings


class DriveNotConfiguredError(Exception):
    """Raised when Google Drive credentials are absent or empty."""


class GoogleDriveService:
    """Thin wrapper around the Google Drive API v3."""

    _MIME_MP4 = "video/mp4"
    _CHUNK = 1024 * 1024  # 1 MB streaming chunks

    def __init__(self, service):
        self._svc = service

    # ── public API ─────────────────────────────────────────────────────────────

    def list_mp4s_in_folder(self, folder_id: str) -> list[dict]:
        """
        Return all MP4 files directly inside `folder_id`.
        Each dict has: id, name, size, webViewLink, webContentLink.
        """
        results = []
        page_token = None
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType='{self._MIME_MP4}' "
            f"and trashed=false"
        )
        fields = "nextPageToken, files(id,name,size,webViewLink,webContentLink)"
        while True:
            resp = (
                self._svc.files()
                .list(
                    q=query,
                    fields=fields,
                    pageSize=100,
                    pageToken=page_token,
                )
                .execute()
            )
            results.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return results

    def list_subfolders(self, parent_id: str) -> list[dict]:
        """Return immediate subfolder entries (id, name) inside `parent_id`."""
        resp = (
            self._svc.files()
            .list(
                q=(
                    f"'{parent_id}' in parents "
                    f"and mimeType='application/vnd.google-apps.folder' "
                    f"and trashed=false"
                ),
                fields="files(id,name)",
                pageSize=50,
            )
            .execute()
        )
        return resp.get("files", [])

    def stream_file(self, drive_file_id: str, range_header: str | None) -> StreamingResponse:
        """
        Stream an MP4 from Drive to the browser.
        Supports HTTP Range requests for video seeking.
        """
        # Get file metadata to know size
        meta = (
            self._svc.files()
            .get(fileId=drive_file_id, fields="size,mimeType")
            .execute()
        )
        file_size = int(meta.get("size", 0))

        if range_header:
            start, end = _parse_range(range_header, file_size)
            length = end - start + 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": "video/mp4",
            }
            return StreamingResponse(
                _download_range(self._svc, drive_file_id, start, end, self._CHUNK),
                status_code=206,
                headers=headers,
                media_type="video/mp4",
            )

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(
            _download_full(self._svc, drive_file_id, self._CHUNK),
            status_code=200,
            headers=headers,
            media_type="video/mp4",
        )


# ── module-level factory ───────────────────────────────────────────────────────

_cached_service: "GoogleDriveService | None" = None


def get_drive_service() -> GoogleDriveService:
    """
    Build and cache a GoogleDriveService.
    Raises DriveNotConfiguredError if credentials are absent.
    """
    global _cached_service
    if _cached_service is not None:
        return _cached_service

    creds_json = settings.google_service_account.strip()
    if not creds_json or creds_json == "{}":
        raise DriveNotConfiguredError("GOOGLE_SERVICE_ACCOUNT is not configured.")

    try:
        creds_data = json.loads(creds_json)
    except json.JSONDecodeError as exc:
        raise DriveNotConfiguredError(f"GOOGLE_SERVICE_ACCOUNT is not valid JSON: {exc}")

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    credentials = service_account.Credentials.from_service_account_info(
        creds_data, scopes=scopes
    )
    raw = build("drive", "v3", credentials=credentials)
    _cached_service = GoogleDriveService(raw)
    return _cached_service


# ── streaming helpers ──────────────────────────────────────────────────────────

def _parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse 'bytes=start-end' header. Returns (start, end) clamped to file size."""
    try:
        unit, ranges = range_header.split("=")
        start_str, end_str = ranges.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Invalid Range header.",
        )
    end = min(end, file_size - 1)
    if start > end or start < 0:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Unsatisfiable range.",
        )
    return start, end


def _download_full(svc, file_id: str, chunk_size: int) -> Generator[bytes, None, None]:
    from googleapiclient.http import MediaIoBaseDownload
    import io
    fh = io.BytesIO()
    request = svc.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
    done = False
    while not done:
        _, done = downloader.next_chunk()
        fh.seek(0)
        yield fh.read()
        fh.seek(0)
        fh.truncate(0)


def _download_range(svc, file_id: str, start: int, end: int, chunk_size: int) -> Generator[bytes, None, None]:
    """Stream a byte range from Drive iteratively in chunks to avoid OOM."""
    request = svc.files().get_media(fileId=file_id)
    uri = request.uri
    http = svc._http

    current_start = start
    while current_start <= end:
        current_end = min(current_start + chunk_size - 1, end)
        
        headers = dict(request.headers)
        headers["Range"] = f"bytes={current_start}-{current_end}"
        
        # http.request handles auth automatically since it's an AuthorizedHttp object
        resp, content = http.request(uri, headers=headers)
        
        if resp.status not in (200, 206) or not content:
            break
            
        yield content
        # Advance by the exact number of bytes received in case the server chunked it differently
        current_start += len(content)
