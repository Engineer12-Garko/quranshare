# QuranFlow — Design: Automatic Google Drive Synchronization

## 1. Current Sync Architecture

**Manual admin-triggered sync (existing)**

- **Endpoint**: `POST /admin/sync` (admin-only, `require_role("admin")`)
- **Implementation**: `sync_drive(db: Session)` in `app/services/sync.py`
- **Algorithm**:
  1. Fetch all MP4 files from Google Drive (recursive folder traversal)
  2. Build set of existing `drive_file_id` values from DB
  3. For each Drive file:
     - If `drive_file_id` exists in DB → update metadata (title, links, `is_active=True`)
     - If not → insert new `Video` record
  4. Deactivate DB records whose `drive_file_id` no longer exists in Drive
  5. `db.commit()` — atomic
- **Trigger**: Human admin clicks "Sync" in the admin panel
- **Frequency**: On-demand, triggered by admin
- **Failure mode**: Returns error JSON; admin must retry

**Limitations**: Requires human admin intervention; not automatic.

---

## 2. Scheduled Polling Architecture

**How it would work**:

- A cron-like scheduled job runs on the backend (Vercel Server Functions, Cloud Scheduler, or similar)
- Job calls `sync_drive(db)` on a regular interval (e.g., every 15 minutes, hourly)
- Job runs as a system process — no user authentication required
- Job uses backend's Google Drive credentials (service account from env vars)

**Architecture diagram**:

```
┌─────────────────────────────────────────────────────┐
│   Vercel Platform                                 │
│ ─────────────────────┬───────────────────────────────▶ │
│                     │  Scheduled Trigger (cron)              │
│   Server Function   ├───────────────────────────────▶ │
│   (sync_drive)      ├───────────────────────────────▶ │
│                     │  ▶ Fetch Drive files                    │
│                     │  ▶ Compare with DB                     │
│                     │  ▶ Insert/update/deactivate             │
│                     │  ▶ db.commit()                          │
│                     │  ◀ Return summary (logged only)       │
│                     └──────────────────────────────◀ │
└─────────────────────────────────────────────────────┘

**Reliability**: High — regular interval ensures eventual consistency

**Implementation complexity**: Moderate
- Need to schedule the job on Vercel (Vercel Cron Jobs, or a separate Node/Python worker)
- Minimal code changes — reuse existing `sync_drive()` function
- Need to handle idempotency (already designed into `sync_drive`)

**Vercel compatibility**: 
- Vercel Server Functions can be scheduled via cron jobs
- Alternatively, a separate always-running service (but that costs more)
- Server Functions are cold-start friendly for infrequent syncs

**Credential requirements**: Same as current — service account JSON in `GOOGLE_SERVICE_ACCOUNT` env var; `GOOGLE_DRIVE_ROOT_FOLDER_ID` env var

**Failure recovery**: 
- If sync fails, error is logged; next scheduled run retries
- No manual intervention required (ideally)
- Errors appear in function logs

**Duplicate handling**: Already handled — `drive_file_id` UNIQUE check; existing records are updated, not duplicated

**Deleted file detection**: 
- Scan all DB `drive_file_id` values against Drive results
- Deactivate (not delete) records whose file is gone
- Preserve posting history (as per requirements)

**Compute cost**: 
- very low for infrequent syncs (e.g., every 15 min)
- Server Function invocations are billable per execution; ~$0.0001 per invocation on Vercel

---

## 3. Webhook Architecture (Google Drive Push Notifications)

**How it would work**:

- Google Drive sends an HTTP POST to a QuranFlow endpoint when changes occur in the watched folder
- Payload includes: file ID, change type (upload, update, delete, rename), folder ID
- Endpoint validates the notification, then triggers `sync_drive()` or targeted updates

**Architecture diagram**:

```
┌─────────────────────────────────────────────────────┐
│   Google Drive                                    │
│ ──────────────────────▶│  Webhook endpoint (POST)           │
│  (file created/changed/deleted)                   │
│                     │  ▶ Validate notification token       │
│                     │  ▶ Call sync_drive() or targeted API │
│                     │  ◀ Return 200 OK                      │
│                     └──────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│   QuranFlow Backend                                 │
│                                                   │
└─────────────────────────────────────────────────────┘
```

**Reliability**: 
- Google guarantees at-least-once delivery
- May miss events if endpoint is down; needs retry logic
- Better than polling for near-real-time sync

**Implementation complexity**: High
- Must set up Google Cloud Domain-wide Delegation or OAuth consent screen
- Must verify webhook tokens (Google signs them)
- Must handle retry/backoff for failed deliveries
- Must handle duplicate events
- Must configure the correct notification ID resource name

**Vercel compatibility**: 
- Difficult — Vercel Server Functions have time limits (typically 10s max)
- Webhooks require a publicly reachable endpoint with SSL
- Vercel URLs can be public but may change; need custom domain + SSL
- Not ideal for this use case

**Credential requirements**: Same service account, but must also register webhook URLs with Google Drive API; must keep webhook secret/token secure

**Failure recovery**: 
- Google retries delivery; if endpoint consistently returns error, notifications stop
- Must have fallback polling schedule if webhooks stop working
- Need idempotency to handle duplicate deliveries

**Duplicate handling**: Events may be delivered more than once; `sync_drive` must be idempotent (already designed)

**Deleted file detection**: 
- Webhook `changed` type with file removal triggers deactivation
- Still need periodic scan to catch events that were missed

**Compute cost**: 
- Per-event — very low if few changes
- But infrastructure overhead (webhook endpoint, token management) is higher

---

## 4. Comparison

| Aspect                     | Scheduled Polling        | Webhook                      |
|----------------------------|--------------------------|------------------------------|
| Reliability                | High (eventual consistency) | Medium (at-least-once, may miss) |
| Implementation complexity  | Low                      | High                         |
| Vercel compatibility       | High                     | Low                          |
| Credential requirements    | Same as current          | Same + webhook config        |
| Failure recovery           | Next scheduled run       | Google retries + manual      |
| Duplicate handling         | Built-in (idempotent)    | Must handle manually         |
| Deleted file detection    | Yes (per scan)           | Yes (per event) + periodic   |
| Compute cost               | Very low                 | Very low per-event + overhead|
| Real-time latency          | Minutes (configurable)   | Seconds                      |
| Complexity of V1           | **Simple**               | **Complex**                  |

---

## 5. Recommended V1 Approach: **Scheduled Polling**

**Why**: 
- Simplest robust V1 — minimal code changes
- Full Vercel compatibility
- No new credentials or config beyond existing
- Proven pattern (cron + function call)
- Idempotency already designed into `sync_drive`
- Can be upgraded to webhooks later

**Recommended schedule**: Every 15 minutes (adjustable later)

**Rationale**: 
- Provides near-real-time sync for most use cases
- YouTube/Drive creators typically upload once per video
- 15-minute latency is acceptable for a daily reminder app
- Avoids the complexity of webhook setup and maintenance

---

## 6. Files Likely to Change

**New/modified files**:

1. `app/services/sync.py` — may need minor changes for idempotent retry logic
2. `app/config.py` — add `SYNC_SCHEDULE_MINUTES` env var (default 15)
3. `app/main.py` (or Vercel entry point) — schedule the cron job
4. `app/routes/admin.py` — may retain `POST /admin/sync` as internal/debug endpoint (or remove)
5. `app/database.py` / models — no changes needed (existing `drive_file_id`, `is_active` fields suffice)

**Files NOT to change** (per requirements):
- Frontend `app/static/js/app.js`
- Auth routes
- WhatsApp sharing code
- Google Drive streaming code

---

## 7. Database Changes

**No schema changes required** — existing fields suffice:

- `Video.drive_file_id` (VARCHAR, UNIQUE) — the Drive file ID idempotency key
- `Video.is_active` (BOOLEAN) — set `False` for deleted files, keep record
- `Video.title`, `Video.drive_web_view_link`, `Video.drive_download_link` — updated on sync
- `Video.category_id` — already `None` (categories no longer used per current code)

**What the sync does**:

- `drive_file_id UNIQUE` constraint prevents duplicates
- On re-sync: `if drive_file_id exists → update; else → insert`
- Deleted files: `is_active = False` (not `DELETE`)

---

## 8. Security Considerations

**Google credentials**:

- Remain backend-only — never exposed to frontend or users
- Service account has `drive.readonly` scope (read-only access)
- No user authentication required for the sync job
- Credentials from `GOOGLE_SERVICE_ACCOUNT` and `GOOGLE_DRIVE_ROOT_FOLDER_ID` env vars

**Job isolation**:

- Sync job must NOT accept `user_id` or `role` from request body
- Job runs as a system process, not triggered by user action
- No auth cookies, sessions, or tokens needed

**Error handling**:

- Errors logged (no sensitive data exposed)
- If Drive API quotas exceeded, sync backs off and retries next interval
- No partial state — atomic `db.commit()` at end

**Least privilege**: Service account should only have read access to the specific Drive folder; no write/delete access needed (sync only updates DB, doesn't modify Drive).

---

## 9. Failure/Retry Strategy

**Primary approach**: Scheduled polling with automatic retry

**Behaviors**:

1. **Sync succeeds**: Returns summary; next run scheduled at interval
2. **Sync fails** ( Drive API error, quota exceeded, network error ):
   - Error logged to function logs
   - `return {"success": False, "error": "..."}` 
   - Next scheduled run attempts again
3. **Chronic failures**: After 3 consecutive failures, could:
   - Send alert (email/Slack) — optional V2
   - Continue trying; doesn't block app functionality
   - Manual admin sync still available as fallback

**Idempotency guarantees**:

- `drive_file_id UNIQUE` prevents duplicate inserts
- `UPDATE` on existing records is idempotent
- `is_active = True` reset on each successful sync
- Deactivation of removed files is idempotent

**Manual fallback**: Admin-initiated `POST /admin/sync` retained for:
- Initial setup
- Emergency recovery if scheduled sync breaks
- Debugging

---

## 10. Interaction with Future FFmpeg Processing

**Future pipeline**:

```
Google Drive
    ▼ (automatic sync)
QuranFlow DB (Video records with drive_file_id)
    ▼ (media processing - future)
Optimized/Compressed MP4
    ▼ (share)
WhatsApp Status / Library
```

**Design considerations for V1**:

- Keep DB fields clean: `drive_file_id`, `drive_web_view_link`, `drive_download_link`
- No compression or optimization in V1 — just sync metadata
- The `drive_download_link` from Google Drive streaming already serves the original video
- Future step: add a job that downloads each active video, runs FFmpeg, stores optimized version, updates DB with new path
- V1 sync lays the groundwork: we already know which Drive files exist, which videos are active, and the idempotency patterns

**No code changes for FFmpeg in V1** — just the sync architecture.

---

## 11. Proposed Sync Sequence (V1)

```
Every 15 minutes (configurable):

1. Scheduled trigger fires (Vercel Cron Job)
2. Server function: sync_drive(db)
3. Initialize Google Drive service (service account creds)
4. root_folder = GOOGLE_DRIVE_ROOT_FOLDER_ID
5. Fetch all MP4 files recursively from Drive
6. Build set of existing drive_file_ids from DB
7. FOR each Drive file:
     - If drive_file_id in DB → UPDATE title, links, is_active=True
     - Else → INSERT new Video record (drive_file_id, title, links, is_active=True)
8. FOR each DB Video with drive_file_id:
     - If drive_file_id NOT in Drive results → set is_active=False
9. db.commit()
10. Return summary: {success, added, updated, deactivated, failed, errors}
11. Log summary; no user-visible output
12. Next scheduled run in 15 minutes
```

---

## 12. Tests Required

**Unit tests** (new or existing):

1. `test_sync_drive_no_creds` — `DriveNotConfiguredError` handled, returns `{"success": False, "error": "..."}`
2. `test_sync_drive_adds_new_file` — new Drive file inserted as Video record
3. `test_sync_drive_updates_existing` — existing Drive file metadata updated
4. `test_sync_drive_deactivates_removed` — DB record `is_active=False` when Drive file gone
5. `test_sync_drive_idempotent` — running sync twice produces same DB state (no duplicates)
6. `test_sync_drive_root_folder_missing` — `GOOGLE_DRIVE_ROOT_FOLDER_ID` not configured
7. `test_sync_drive_error_handling` — individual file errors don't halt entire sync

**Integration tests**:

8. End-to-end: add MP4 to Drive → wait for scheduled sync → verify appears in Library
9. End-to-end: remove MP4 from Drive → wait for sync → verify `is_active=False` in DB, record preserved

**Note**: Integration tests require a real Google Drive account and test MP4 files — may be mocked for unit test suite.

---

## Summary

| Item                     | Decision / Recommendation                                                  |
|--------------------------|-----------------------------------------------------------------------------|
| **V1 approach**          | Scheduled polling every 15 minutes                                          |
| **Trigger mechanism**    | Vercel Cron Job calling `sync_drive()` server function                       |
| **Deleted files**        | Set `is_active=False`; preserve DB records and posting history               |
| **Duplicates**           | Prevented by `drive_file_id UNIQUE`                                         |
| **Security**             | Backend-only service account creds; no public endpoints                       |
| **Failure handling**     | Automatic retry on next scheduled run; admin sync retained as fallback         |
| **Future FFmpeg**        | Laid groundwork; V1 only syncs metadata; compression step added later          |
| **Code changes**         | Minimal: `sync.py` tweaks, `config.py` new var, cron job entry point           |
| **Test effort**          | ~7 unit tests + optional integration tests                                    |

---

## Implementation Checklist

- [ ] Add `SYNC_SCHEDULE_MINUTES = 15` to `app/config.py`
- [ ] Ensure `GOOGLE_DRIVE_ROOT_FOLDER_ID` is set in Vercel env vars
- [ ] Add Vercel Cron Job schedule (e.g., `0 */15 * * *` for every 15 min)
- [ ] Add `POST /admin/sync` retained as internal endpoint (or document removal)
- [ ] Write unit tests for `sync_drive()` (7 test cases above)
- [ ] Document the sync sequence for ops team
- [ ] Monitor first few runs to tune interval if needed
- [ ] Plan webhook upgrade path for V2 (if/when requirements change)

**Do NOT modify code** — this report is design-only. Implementation would follow in subsequent tickets.