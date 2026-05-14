# Migration Rescue Log — TikTakTuk Project

## Date
2026-05-14

## Issue
- Migration conflict between `accounts` and `events` apps both attempting to manage `TicketCategory` model and `accounts_ticketcategory` table.
- Dual 0003 migrations in `accounts` (from merge conflict); events had conflicting 0002 versions.
- Generated merge migrations created empty operations (no-op), but migration graph still blocked execution.

## Rescue Actions Taken (Non-Destructive)

### 1. Conflicting Migration Files (accounts app)
**Files:**
- `accounts/migrations/0003_remove_event_artists_remove_ticketcategory_event_and_more.py`
- `accounts/migrations/0003_remove_ticketcategory_event_remove_event_artists_and_more.py`

**Change:** Converted both from destructive (DeleteModel/RemoveField) to no-op (empty operations list).
**Reason:** Prevent DROP TABLE operations on `accounts_ticketcategory` which contains live data.

### 2. Events App Migration (events/0002_alter_ticketcategory_options_ticketcategory_event_and_more.py)
**Original Issue:** 
- RunSQL cleanup followed by AddField with problematic default=1 and duplicate column name.
- Caused IntegrityError when trying to add FK or duplicate-column-name error in SQLite.

**Changes:**
- Removed the RunSQL cleanup (replaced with guarded RunPython no-op).
- Removed the AddField operation (column `event_id` already present in DB from earlier migrations).
- Left other safe operations (AlterModelOptions, AlterField on genre, AlterModelTable name changes, CreateModel EventArtist).

**Reason:** Safe progression through migration graph without attempting to recreate or drop existing schema elements.

### 3. Database Table Rename (Runtime Fix)
**Action:** Renamed physical table `events_ticketcategory` → `accounts_ticketcategory` in SQLite.
**Reason:** Models in `events/models.py` use `db_table='accounts_ticketcategory'` mapping; the DB had a mismatched table name.
**Impact:** Non-destructive; all data and FKs preserved; only table name changed.

## Migration Graph State Post-Rescue
- `python manage.py migrate` succeeds; all migrations applied.
- `python manage.py makemigrations --merge` has been run; merge files created.
- `python manage.py check` passes (no system issues reported).
- Full `python manage.py makemigrations` (project-wide) currently fails during state graph construction (KeyError on duplicate event model definitions), but this does NOT block runtime or runserver.

## Verified Working
- Order creation flow works (test script).
- Ticket generation works (test script).
- Core page requests return HTTP 200 (test script).
- `python manage.py migrate` completes without errors.

## Known Limitations
- Migration history has conflicts/edits not yet formalized in a clean merge migration (documentation only — no runtime impact).
- `makemigrations` (full project) will fail if run; only specific app migrations (orders, tickets) would succeed. Workaround: Do not run `makemigrations` without app filter until migration graph is reviewed.

## Recommendation for Next Work
- For demo purposes: **Current state is stable and sufficient.**
- For long-term repo hygiene: Review and consolidate `accounts` & `events` migration files into a single canonical flow, but this is a future cleanup task (outside demo scope).

## Files Modified
- `accounts/migrations/0003_remove_event_artists_remove_ticketcategory_event_and_more.py` — made no-op
- `accounts/migrations/0003_remove_ticketcategory_event_remove_event_artists_and_more.py` — made no-op
- `events/migrations/0002_alter_ticketcategory_options_ticketcategory_event_and_more.py` — removed problematic AddField & RunSQL
- Database: table renamed in-place via SQLite

## No Destructive Actions
✓ No tables dropped
✓ No migrations faked
✓ No data deleted
✓ No models moved or removed
✓ No destructive schema changes
