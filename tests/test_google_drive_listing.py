"""Regression coverage for complete, shared-drive-aware folder enumeration."""

from app.services.google_drive import GoogleDriveService


def test_list_subfolders_follows_all_pages_and_supports_shared_drives():
    calls = []
    pages = [
        {"files": [{"id": f"folder-{i}", "name": f"Folder {i}"} for i in range(100)], "nextPageToken": "next-page"},
        {"files": [{"id": "folder-100", "name": "Folder 100"}]},
    ]

    class Request:
        def __init__(self, page):
            self.page = page

        def execute(self):
            return self.page

    class Files:
        def list(self, **kwargs):
            calls.append(kwargs)
            return Request(pages[len(calls) - 1])

    class Service:
        def files(self):
            return Files()

    folders = GoogleDriveService(Service()).list_subfolders("root")

    assert len(folders) == 101
    assert folders[-1]["id"] == "folder-100"
    assert len(calls) == 2
    assert calls[0]["pageToken"] is None
    assert calls[1]["pageToken"] == "next-page"
    assert calls[0]["supportsAllDrives"] is True
    assert calls[0]["includeItemsFromAllDrives"] is True
    assert "nextPageToken" in calls[0]["fields"]
