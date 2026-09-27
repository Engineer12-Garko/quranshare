import re

sync_py = r"app\services\sync.py"

with open(sync_py, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the sync logic in sync_drive to crawl folders recursively
new_logic = """
    # O(n) hash set of existing drive_file_ids in the database
    existing: dict[str, Video] = {
        v.drive_file_id: v
        for v in db.query(Video).all()
    }

    added = updated = deactivated = failed = 0
    errors: list[str] = []
    seen_drive_ids: set[str] = set()
    
    # Breadth-first search queue to crawl folders recursively
    folders_to_process = [root_folder]

    while folders_to_process:
        current_folder = folders_to_process.pop(0)
        
        # 1. Fetch subfolders of current folder and add to queue
        try:
            subfolders = drive.list_subfolders(current_folder)
            for sf in subfolders:
                folders_to_process.append(sf["id"])
        except Exception as exc:
            errors.append(f"Failed to list subfolders for {current_folder}: {exc}")
            failed += 1
            continue
            
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
                    video.title = f.get("name", video.title)
                    video.category_id = None # We no longer use categories
                    video.drive_web_view_link = f.get("webViewLink")
                    video.drive_download_link = f.get("webContentLink")
                    video.is_active = True
                    updated += 1
                else:
                    # Insert new record
                    video = Video(
                        drive_file_id=drive_id,
                        title=f.get("name", drive_id),
                        category_id=None,
                        drive_web_view_link=f.get("webViewLink"),
                        drive_download_link=f.get("webContentLink"),
                        is_active=True,
                    )
                    db.add(video)
                    added += 1
            except Exception as exc:
                errors.append(f"File '{drive_id}': {exc}")
                failed += 1

    # Deactivate videos whose Drive file is gone (O(n) scan)
"""

content = re.sub(r'# O\(n\) hash set of existing drive_file_ids.*?# Deactivate videos whose Drive file is gone \(O\(n\) scan\)', new_logic.strip() + '\n\n    # Deactivate videos whose Drive file is gone (O(n) scan)', content, flags=re.DOTALL)

with open(sync_py, "w", encoding="utf-8") as f:
    f.write(content)
