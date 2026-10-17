"""
Drive synchronization service.

Algorithm (O(n) using a hash set for duplicate detection per DSA spec):
  existing_ids = set(all drive_file_ids in DB)
  for each Drive file:
      if id in existing_ids → update
      else                  → insert
  deactivate rows whose drive_file_id is no longer in Drive
"""
from collections import deque

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.video import Video


def sync_drive(db: Session) -> dict:
    """
    Synchronise Google Drive content into the videos table.
    Returns a summary dict: {success, added, updated, deactivated, failed, errors}.
    """
    from app.services.google_drive import get_drive_service, DriveNotConfiguredError
    from app.config import settings

    try:
        drive = get_drive_service()
    except DriveNotConfiguredError as exc:
        return {"success": False, "error": str(exc)}

    root_folder = settings.google_drive_root_folder_id
    if not root_folder:
        return {"success": False, "error": "GOOGLE_DRIVE_ROOT_FOLDER_ID is not configured."}

    # Build category-name → category-id lookup map (O(1) per lookup)
    category_map: dict[str, int] = {
        c.name.lower(): c.id
        for c in db.query(Category).filter(Category.is_active.is_(True)).all()
    }

    # O(n) hash set of existing drive_file_ids in the database
    existing: dict[str, Video] = {
        v.drive_file_id: v
        for v in db.query(Video).all()
    }

    added = updated = deactivated = failed = 0
    errors: list[str] = []
    seen_drive_ids: set[str] = set()
    
    # Breadth-first search queue to crawl folders recursively.
    # The root folder is not itself a category; immediate child folders are.
    folders_to_process = deque([(root_folder, None)])
    visited_folders: set[str] = set()

    while folders_to_process:
        current_folder, category_id = folders_to_process.popleft()
        if current_folder in visited_folders:
            continue
        visited_folders.add(current_folder)
        
        # 1. Fetch subfolders of current folder and add to queue
        try:
            subfolders = drive.list_subfolders(current_folder)
            for sf in subfolders:
                subfolder_category_id = category_map.get(
                    sf.get("name", "").strip().lower(),
                    category_id,
                )
                folders_to_process.append((sf["id"], subfolder_category_id))
        except Exception as exc:
            errors.append(f"Failed to list subfolders for {current_folder}: {exc}")
            failed += 1
            
        # 2. Fetch MP4s in current folder
        try:
            files = drive.list_mp4s_in_folder(current_folder)
        except Exception as exc:
            errors.append(f"Folder '{current_folder}': {exc}")
            failed += 1
            continue

        for f in files:
            drive_id = f["id"]
            seen_drive_ids.add(drive_id)

            try:
                if drive_id in existing:
                    # Update existing record (O(1) lookup)
                    video = existing[drive_id]
                    values = {
                        "title": f.get("name", video.title),
                        "category_id": category_id,
                        "drive_web_view_link": f.get("webViewLink"),
                        "drive_download_link": f.get("webContentLink"),
                        "is_active": True,
                    }
                    changed = False
                    for field, value in values.items():
                        if getattr(video, field) != value:
                            setattr(video, field, value)
                            changed = True
                    if changed:
                        updated += 1
                else:
                    # Insert new record
                    video = Video(
                        drive_file_id=drive_id,
                        title=f.get("name", drive_id),
                        category_id=category_id,
                        drive_web_view_link=f.get("webViewLink"),
                        drive_download_link=f.get("webContentLink"),
                        is_active=True,
                    )
                    db.add(video)
                    existing[drive_id] = video
                    added += 1
            except Exception as exc:
                errors.append(f"File '{drive_id}': {exc}")
                failed += 1

    # Only a complete scan can establish that a file disappeared. If any
    # folder failed to list, keep the existing catalog active rather than
    # treating unseen files in that subtree as deleted.
    if not errors:
        for drive_id, video in existing.items():
            if drive_id not in seen_drive_ids and video.is_active:
                video.is_active = False
                deactivated += 1

    db.commit()

    return {
        "success": not errors,
        "added": added,
        "updated": updated,
        "deactivated": deactivated,
        "failed": failed,
        "errors": errors,
    }
