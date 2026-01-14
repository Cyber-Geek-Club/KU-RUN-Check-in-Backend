# 📸 Participant Snapshots API Documentation

## Overview

ระบบ Participant Snapshots ช่วยให้คุณสามารถบันทึก "ภาพรวม" (snapshot) ของผู้เข้าร่วมกิจกรรมในแต่ละช่วงเวลา และดูประวัติย้อนหลังได้

## Features

✅ สร้าง snapshot ของ participants อัตโนมัติหรือ manual  
✅ เก็บข้อมูลแต่ละ participant พร้อม metadata  
✅ ดูประวัติ snapshots ทั้งหมดของ event  
✅ ดู entries ในแต่ละ snapshot แบบ paginated  
✅ Unique keys (snapshot_id, entry_id) สำหรับแต่ละ record  

## Database Schema

### Table: `participant_snapshots`
```sql
- id: SERIAL PRIMARY KEY
- snapshot_id: VARCHAR(36) UNIQUE (UUID)
- event_id: INTEGER (FK to events)
- snapshot_time: TIMESTAMP WITH TIME ZONE
- entry_count: INTEGER
- created_by: INTEGER (FK to users)
- description: VARCHAR(500)
```

### Table: `participant_snapshot_entries`
```sql
- id: SERIAL PRIMARY KEY
- entry_id: VARCHAR(36) UNIQUE (UUID)
- snapshot_id: INTEGER (FK to participant_snapshots)
- participation_id: INTEGER
- user_id: INTEGER
- user_name: VARCHAR(255)
- user_email: VARCHAR(255)
- action: VARCHAR(50)
- status: VARCHAR(50)
- created_at: TIMESTAMP WITH TIME ZONE
- joined_at: TIMESTAMP WITH TIME ZONE
- checked_in_at: TIMESTAMP WITH TIME ZONE
- completed_at: TIMESTAMP WITH TIME ZONE
- metadata: JSONB
```

## API Endpoints

### 1. Get Participant Snapshots History

**Endpoint:** `GET /api/events/{eventId}/participants/history`

**Description:** ดึง list ของ snapshots ทั้งหมดของ event

**Query Parameters:**
- `page` (int, default: 1): หน้าที่ต้องการ
- `page_size` (int, default: 20, max: 100): จำนวนรายการต่อหน้า

**Response:**
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "snapshots": [
    {
      "id": 1,
      "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
      "snapshot_time": "2026-01-14T10:30:00Z",
      "entry_count": 125,
      "description": "Morning snapshot"
    }
  ]
}
```

**Example:**
```bash
curl -X GET "http://localhost:8001/api/events/11/participants/history?page=1&page_size=20" \
  -H "Authorization: Bearer {token}"
```

---

### 2. Get Snapshot Entries

**Endpoint:** `GET /api/events/{eventId}/participants/history/{snapshotId}/entries`

**Description:** ดึง entries ทั้งหมดของ snapshot

**Path Parameters:**
- `eventId` (int): ID ของ event
- `snapshotId` (string): UUID ของ snapshot

**Query Parameters:**
- `page` (int, default: 1): หน้าที่ต้องการ
- `page_size` (int, default: 50, max: 200): จำนวนรายการต่อหน้า

**Response:**
```json
{
  "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot_time": "2026-01-14T10:30:00Z",
  "total_entries": 125,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "entries": [
    {
      "id": 1,
      "entry_id": "660e9500-f30c-52e5-b827-557766551111",
      "snapshot_id": 1,
      "participation_id": 42,
      "user_id": 10,
      "user_name": "John Doe",
      "user_email": "john@example.com",
      "action": "checked_in",
      "status": "checked_in",
      "created_at": "2026-01-14T10:30:00Z",
      "joined_at": "2026-01-14T08:00:00Z",
      "checked_in_at": "2026-01-14T09:00:00Z",
      "completed_at": null,
      "metadata": {
        "join_code": "12345",
        "checkin_date": "2026-01-14",
        "proof_image_url": "https://..."
      }
    }
  ]
}
```

**Example:**
```bash
curl -X GET "http://localhost:8001/api/events/11/participants/history/550e8400-e29b-41d4-a716-446655440000/entries?page=1&page_size=50" \
  -H "Authorization: Bearer {token}"
```

---

### 3. Create New Snapshot (Manual)

**Endpoint:** `POST /api/events/{eventId}/participants/snapshots`

**Description:** สร้าง snapshot ใหม่แบบ manual

**Path Parameters:**
- `eventId` (int): ID ของ event

**Query Parameters:**
- `description` (string, optional): คำอธิบาย snapshot

**Response:**
```json
{
  "id": 1,
  "snapshot_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": 11,
  "snapshot_time": "2026-01-14T10:30:00Z",
  "entry_count": 125,
  "created_by": 1,
  "description": "Manual snapshot for reporting"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8001/api/events/11/participants/snapshots?description=End%20of%20day%20snapshot" \
  -H "Authorization: Bearer {token}"
```

---

### 4. Delete Snapshot

**Endpoint:** `DELETE /api/events/{eventId}/participants/history/{snapshotId}`

**Description:** ลบ snapshot (และ entries ทั้งหมด)

**Path Parameters:**
- `eventId` (int): ID ของ event
- `snapshotId` (string): UUID ของ snapshot

**Response:** `204 No Content`

**Example:**
```bash
curl -X DELETE "http://localhost:8001/api/events/11/participants/history/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer {token}"
```

---

## Installation & Setup

### 1. Run Migration

```bash
python -m src.migrate.migrate_participant_snapshots
```

### 2. Verify Tables

```sql
SELECT * FROM participant_snapshots LIMIT 5;
SELECT * FROM participant_snapshot_entries LIMIT 5;
```

### 3. Test API

```bash
# Create a snapshot
curl -X POST "http://localhost:8001/api/events/11/participants/snapshots" \
  -H "Authorization: Bearer {token}"

# Get snapshots
curl -X GET "http://localhost:8001/api/events/11/participants/history" \
  -H "Authorization: Bearer {token}"
```

---

## Usage Scenarios

### Scenario 1: Daily Report

สร้าง snapshot ทุกวันเวลา 23:59 เพื่อเก็บสถิติรายวัน:

```python
# ใน scheduler_service.py
@scheduler.scheduled_job('cron', hour=23, minute=59)
async def create_daily_snapshot():
    # สร้าง snapshot สำหรับทุก active events
    pass
```

### Scenario 2: Export History

Export ข้อมูล participants ในช่วงเวลาที่ต้องการ:

```python
# Get snapshot at specific time
snapshots = await get_snapshots_by_event(db, event_id=11, page=1, page_size=100)

# Export entries
for snapshot in snapshots:
    entries = await get_snapshot_entries(db, snapshot.snapshot_id, page=1, page_size=1000)
    # Export to CSV/Excel
```

### Scenario 3: Audit Trail

ตรวจสอบการเปลี่ยนแปลงของ participants ตามช่วงเวลา:

```python
# Compare snapshots
snapshot_1 = await get_snapshot_entries(db, "snapshot-id-1")
snapshot_2 = await get_snapshot_entries(db, "snapshot-id-2")

# Find differences
added = [e for e in snapshot_2.entries if e.user_id not in [x.user_id for x in snapshot_1.entries]]
removed = [e for e in snapshot_1.entries if e.user_id not in [x.user_id for x in snapshot_2.entries]]
```

---

## Frontend Integration

### Display Snapshots List

```typescript
// Fetch snapshots
const response = await fetch(`/api/events/${eventId}/participants/history?page=1&page_size=20`);
const data = await response.json();

// Display in table
data.snapshots.forEach(snapshot => {
  console.log(`Snapshot: ${snapshot.snapshot_id}`);
  console.log(`Time: ${snapshot.snapshot_time}`);
  console.log(`Entries: ${snapshot.entry_count}`);
});
```

### Display Entries with Unique Keys

```typescript
// Fetch entries
const response = await fetch(`/api/events/${eventId}/participants/history/${snapshotId}/entries`);
const data = await response.json();

// Use entry_id as unique key
data.entries.forEach(entry => {
  // entry.entry_id is unique UUID
  <TableRow key={entry.entry_id}>
    <TableCell>{entry.user_name}</TableCell>
    <TableCell>{entry.status}</TableCell>
  </TableRow>
});
```

---

## Performance Considerations

1. **Indexes**: ทุก UUID fields มี index แล้ว
2. **Pagination**: ใช้ pagination เสมอสำหรับ large datasets
3. **Cascade Delete**: ลบ snapshot จะลบ entries อัตโนมัติ
4. **JSON Metadata**: ใช้ JSONB สำหรับข้อมูลที่ยืดหยุ่น

---

## Error Handling

```json
{
  "detail": "Snapshot not found"
}
```

Common errors:
- `404`: Snapshot not found
- `400`: Invalid parameters
- `401`: Unauthorized
- `403`: Forbidden (ต้องเป็น staff/organizer)

---

## Testing

```bash
# 1. Create test snapshot
POST /api/events/11/participants/snapshots

# 2. Get snapshots
GET /api/events/11/participants/history

# 3. Get entries
GET /api/events/11/participants/history/{snapshot_id}/entries

# 4. Delete snapshot
DELETE /api/events/11/participants/history/{snapshot_id}
```

---

## Files Created

```
✨ New Files:
├── src/models/participant_snapshot.py
├── src/schemas/participant_snapshot_schema.py
├── src/crud/participant_snapshot_crud.py
├── src/api/endpoints/participant_snapshots.py
├── src/migrate/migrate_participant_snapshots.py
└── PARTICIPANT_SNAPSHOTS_API.md

📝 Modified Files:
└── main.py (added participant_snapshots router)
```

---

## ✅ Complete!

ระบบพร้อมใช้งานแล้ว! 🎉
