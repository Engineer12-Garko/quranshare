"""Tests for assigning Drive folder categories during synchronization."""
from unittest.mock import patch

from app.models.category import Category
from app.models.video import Video


def test_sync_assigns_immediate_drive_folder_category(client, db):
    category = Category(name="Akhirah", is_active=True)
    db.add(category)
    db.flush()

    class FakeDrive:
        def list_subfolders(self, folder_id):
            if folder_id == "root":
                return [{"id": "akh", "name": "Akhirah"}]
            return []

        def list_mp4s_in_folder(self, folder_id):
            if folder_id == "akh":
                return [{"id": "drive-1", "name": "Reminder.mp4"}]
            return []

    with patch("app.services.google_drive.get_drive_service", return_value=FakeDrive()):
        from app.services.sync import sync_drive
        from app.config import settings

        original_root = settings.google_drive_root_folder_id
        settings.google_drive_root_folder_id = "root"
        try:
            result = sync_drive(db)
        finally:
            settings.google_drive_root_folder_id = original_root

    assert result["success"] is True
    video = db.query(Video).filter(Video.drive_file_id == "drive-1").one()
    assert video.category_id == category.id


def test_sync_does_not_deactivate_videos_after_partial_drive_scan(client, db):
    existing = Video(drive_file_id="temporarily-unreachable", title="Keep me", is_active=True)
    db.add(existing)
    db.flush()

    class FailingDrive:
        def list_subfolders(self, folder_id):
            if folder_id == "root":
                return [{"id": "unavailable", "name": "Akhirah"}]
            raise RuntimeError("temporary Drive error")

        def list_mp4s_in_folder(self, folder_id):
            return []

    with patch("app.services.google_drive.get_drive_service", return_value=FailingDrive()):
        from app.services.sync import sync_drive
        from app.config import settings

        original_root = settings.google_drive_root_folder_id
        settings.google_drive_root_folder_id = "root"
        try:
            result = sync_drive(db)
        finally:
            settings.google_drive_root_folder_id = original_root

    db.refresh(existing)
    assert result["success"] is False
    assert result["failed"] == 1
    assert existing.is_active is True
    assert result["deactivated"] == 0
