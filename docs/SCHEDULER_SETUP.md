# 🔓🔒 Auto Unlock/Lock System Setup

## ภาพรวมระบบ

ระบบจะทำงานอัตโนมัติ 2 อย่าง:
1. **Auto-Unlock (00:00)**: สร้างรหัส join_code ใหม่ให้ผู้ที่ลงทะเบียนล่วงหน้าทุกวัน
2. **Auto-Lock (23:59)**: ทำให้รหัสที่ไม่ได้ใช้หมดอายุ

## การติดตั้ง

### 1. ติดตั้ง dependencies

```bash
pip install APScheduler==3.10.4
```

หรือ

```bash
pip install -r requirements.txt
```

### 2. รีสตาร์ท API Server

```bash
uvicorn main:app --reload
```

ระบบจะเริ่ม scheduler อัตโนมัติเมื่อเริ่มต้น server

## การใช้งาน

### สำหรับผู้ใช้งาน

#### 1. ลงทะเบียนล่วงหน้าทั้งกิจกรรม

```http
POST /api/participations/pre-register/{event_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "ลงทะเบียนสำเร็จ! ระบบจะสร้างรหัสอัตโนมัติทุกวัน",
  "first_code": "12345",
  "first_date": "2026-01-15",
  "event_end_date": "2026-02-14"
}
```

#### 2. ตรวจสอบสถานะ

```http
GET /api/participations/pre-register-status/{event_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "is_registered": true,
  "total_codes": 5,
  "active_codes": 1,
  "used_codes": 3,
  "expired_codes": 1,
  "today_code": {
    "code": "67890",
    "date": "2026-01-15",
    "expires_at": "2026-01-15T23:59:59Z"
  }
}
```

#### 3. ดูรหัสที่ใช้งานได้

```http
GET /api/participations/my-codes/{event_id}
Authorization: Bearer <token>
```

#### 4. ยกเลิกการลงทะเบียนล่วงหน้า

```http
DELETE /api/participations/pre-register/{event_id}?reason=ไม่สะดวก
Authorization: Bearer <token>
```

### สำหรับ Staff

Staff ใช้รหัสเดิมในการ check-in:

```http
POST /api/participations/check-in-daily
{
  "join_code": "12345"
}
```

## การทำงานของ Scheduler

### Auto-Unlock (00:00 ทุกวัน)

1. ค้นหากิจกรรม multi-day ที่กำลังดำเนินการ
2. ค้นหาผู้ใช้ที่ลงทะเบียนไว้แล้ว
3. ตรวจสอบว่าวันนี้มีรหัสหรือยัง
4. ตรวจสอบจำนวนครั้งทั้งหมด (max_checkins_per_user)
5. สร้างรหัสใหม่ถ้ายังไม่มี

### Auto-Lock (23:59 ทุกวัน)

1. ค้นหารหัสที่สถานะ JOINED และยังไม่ได้ใช้
2. ตรวจสอบว่าหมดอายุแล้วหรือยัง
3. เปลี่ยนสถานะเป็น EXPIRED

## ตัวอย่างการใช้งาน

### Scenario: กิจกรรม 30 วัน

```
วันที่ 1: ผู้ใช้ลงทะเบียนล่วงหน้า → ได้รหัสวันแรก
วันที่ 2 (00:00): ระบบสร้างรหัสวันที่ 2 อัตโนมัติ
วันที่ 2 (23:59): รหัสวันที่ 2 หมดอายุ (ถ้าไม่ได้ใช้)
วันที่ 3 (00:00): ระบบสร้างรหัสวันที่ 3 อัตโนมัติ
...
```

## Logs

ดู logs ของ scheduler:

```bash
# ดู logs ทั้งหมด
tail -f logs/app.log

# Filter เฉพาะ scheduler
tail -f logs/app.log | grep "scheduler"
```

## Troubleshooting

### รหัสไม่ถูกสร้างอัตโนมัติ

1. ตรวจสอบว่า scheduler กำลังทำงาน:
   - ดู logs เมื่อเริ่ม server ต้องมี "⏰ Scheduler started successfully"

2. ตรวจสอบว่ากิจกรรมเป็น multi-day:
   ```sql
   SELECT id, title, event_type FROM events WHERE event_type = 'multi_day';
   ```

3. ตรวจสอบว่าผู้ใช้ลงทะเบียนแล้ว:
   ```sql
   SELECT * FROM event_participations WHERE event_id = ? AND user_id = ?;
   ```

### รหัสไม่หมดอายุ

1. ตรวจสอบ timezone configuration
2. ตรวจสอบว่า scheduler รัน auto-expire job

### Manual Trigger (สำหรับ Debug)

สร้าง endpoint ชั่วคราวใน participations.py:

```python
@router.post("/debug/trigger-unlock")
async def debug_trigger_unlock(
    current_user: User = Depends(require_organizer)
):
    from src.services.scheduler_service import auto_unlock_daily_codes
    await auto_unlock_daily_codes()
    return {"message": "Triggered auto-unlock"}

@router.post("/debug/trigger-expire")
async def debug_trigger_expire(
    current_user: User = Depends(require_organizer)
):
    from src.services.scheduler_service import auto_expire_unused_codes
    await auto_expire_unused_codes()
    return {"message": "Triggered auto-expire"}
```

## Production Considerations

1. **Database Performance**: ใช้ index บน `checkin_date`, `status`, `code_expires_at`
2. **Monitoring**: ตั้ง alert ถ้า scheduler หยุดทำงาน
3. **Backup Jobs**: ใช้ cron job ภายนอกเป็น backup
4. **Timezone**: ตรวจสอบว่าใช้ timezone ที่ถูกต้อง (UTC หรือ Asia/Bangkok)

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/participations/pre-register/{event_id}` | ลงทะเบียนล่วงหน้าทั้งกิจกรรม |
| GET | `/api/participations/pre-register-status/{event_id}` | ตรวจสอบสถานะการลงทะเบียน |
| DELETE | `/api/participations/pre-register/{event_id}` | ยกเลิกการลงทะเบียนล่วงหน้า |
| GET | `/api/participations/my-codes/{event_id}` | ดูรหัสทั้งหมด |
| POST | `/api/participations/check-in-daily` | Check-in ด้วยรหัส (staff) |
| GET | `/api/participations/daily-stats/{event_id}` | ดูสถิติรายวัน |
