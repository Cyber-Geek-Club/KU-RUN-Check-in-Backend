# 📋 สรุปการเพิ่มฟีเจอร์ Auto Unlock/Lock

## ✅ สิ่งที่เพิ่มเข้ามา

### 1. Dependencies ใหม่
- `APScheduler==3.10.4` - สำหรับ scheduler
- `pytz==2025.2` - สำหรับ timezone
- `tzlocal==5.3.1` - สำหรับ local timezone

### 2. ไฟล์ใหม่

#### `src/services/scheduler_service.py`
ระบบ scheduler ที่จัดการ:
- 🔓 `auto_unlock_daily_codes()` - รันเวลา 00:00 น.
- 🔒 `auto_expire_unused_codes()` - รันเวลา 23:59 น.
- `start_scheduler()` / `shutdown_scheduler()` - เริ่ม/หยุด scheduler

### 3. CRUD Functions ใหม่ใน `event_participation_crud.py`

```python
# ลงทะเบียนล่วงหน้าทั้งกิจกรรม
async def pre_register_for_multi_day_event(db, user_id, event_id)

# ตรวจสอบสถานะการลงทะเบียน
async def get_user_pre_registration_status(db, user_id, event_id)

# ยกเลิกการลงทะเบียน
async def cancel_pre_registration(db, user_id, event_id, reason)
```

### 4. API Endpoints ใหม่ใน `participations.py`

| Endpoint | Method | คำอธิบาย |
|----------|--------|----------|
| `/participations/pre-register/{event_id}` | POST | ลงทะเบียนล่วงหน้า |
| `/participations/pre-register-status/{event_id}` | GET | เช็คสถานะ |
| `/participations/pre-register/{event_id}` | DELETE | ยกเลิก |

### 5. แก้ไข `main.py`
- เพิ่ม logging configuration
- เพิ่ม startup event เรียก `start_scheduler()`
- เพิ่ม shutdown event เรียก `shutdown_scheduler()`

### 6. เอกสาร
- `SCHEDULER_SETUP.md` - คู่มือการตั้งค่าและใช้งาน (ภาษาอังกฤษ)
- `README_SCHEDULER_TH.md` - คู่มือใช้งานฉบับย่อ (ภาษาไทย)
- `test_scheduler.py` - สคริปต์ทดสอบ

## 🔄 การทำงานของระบบ

### Auto-Unlock (00:00 น.)
1. หากิจกรรม multi-day ที่กำลังดำเนินการ
2. หาผู้ใช้ที่ลงทะเบียนล่วงหน้าไว้
3. เช็ควันนี้มีรหัสหรือยัง → ถ้าไม่มี สร้างใหม่
4. เช็คจำนวนครั้งทั้งหมด (max_checkins_per_user)
5. สร้าง join_code และตั้ง expires_at = วันนี้ 23:59 น.

### Auto-Lock (23:59 น.)
1. หารหัสที่สถานะ `JOINED` และ `code_used = False`
2. เช็คว่า `code_expires_at <= now`
3. เปลี่ยนสถานะเป็น `EXPIRED`

## 📊 Flow การใช้งาน

```
[ผู้ใช้] --ลงทะเบียนล่วงหน้า--> [ระบบ]
                                    |
                                    v
                              [สร้างรหัสวันแรก]
                                    |
                                    v
        [ทุกวัน 00:00] --> [สร้างรหัสวันใหม่อัตโนมัติ]
                                    |
                                    v
                              [ผู้ใช้เช็ครหัส]
                                    |
                                    v
                        [นำไป check-in กับ Staff]
                                    |
                                    v
        [ทุกวัน 23:59] --> [รหัสที่ไม่ได้ใช้ → EXPIRED]
```

## 🚀 วิธีเริ่มใช้งาน

### 1. ติดตั้ง dependencies
```bash
pip install -r requirements.txt
```

### 2. รัน server
```bash
uvicorn main:app --reload
```

เมื่อ server เริ่มทำงาน จะเห็น log:
```
🚀 Starting KU RUN Check-in API...
✅ Database initialized
⏰ Scheduler started successfully
   🔓 Auto-unlock: Every day at 00:00
   🔒 Auto-expire: Every day at 23:59
✅ Scheduler started
```

### 3. ทดสอบ (Optional)
```bash
python test_scheduler.py
```

## 📝 ตัวอย่างการใช้งาน API

### ผู้ใช้ลงทะเบียนล่วงหน้า
```bash
curl -X POST "http://localhost:8000/api/participations/pre-register/1" \
  -H "Authorization: Bearer {token}"
```

Response:
```json
{
  "success": true,
  "message": "ลงทะเบียนสำเร็จ! ระบบจะสร้างรหัสอัตโนมัติทุกวัน",
  "first_code": "12345",
  "first_date": "2026-01-15",
  "event_end_date": "2026-02-14"
}
```

### เช็คสถานะ
```bash
curl -X GET "http://localhost:8000/api/participations/pre-register-status/1" \
  -H "Authorization: Bearer {token}"
```

Response:
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

## ⚠️ สิ่งที่ต้องระวัง

1. **Timezone**: ระบบใช้ UTC - อาจต้องปรับตาม timezone ของประเทศ
2. **Database Load**: ถ้ามีผู้ใช้เยอะ ควรเพิ่ม index บน `checkin_date`, `status`
3. **Monitoring**: ควรตั้ง monitoring เพื่อดูว่า scheduler ทำงานปกติ
4. **Backup**: ควรมี cron job สำรอง เผื่อ scheduler ล้ม

## 🔍 Troubleshooting

### ปัญหา: รหัสไม่ถูกสร้างอัตโนมัติ
- เช็ค logs ว่า scheduler เริ่มทำงานหรือยัง
- เช็คว่ากิจกรรมเป็น `event_type = 'multi_day'`
- เช็คว่าผู้ใช้ลงทะเบียนแล้วจริง

### ปัญหา: รหัสไม่หมดอายุ
- เช็ค timezone configuration
- เช็ค `code_expires_at` ในฐานข้อมูล

### Manual Test
สร้าง debug endpoints:
```python
@router.post("/debug/trigger-unlock")
async def debug_trigger_unlock(
    current_user: User = Depends(require_organizer)
):
    from src.services.scheduler_service import auto_unlock_daily_codes
    await auto_unlock_daily_codes()
    return {"message": "OK"}
```

## 📦 Files Changed/Added

```
✨ New Files:
├── src/services/scheduler_service.py
├── SCHEDULER_SETUP.md
├── README_SCHEDULER_TH.md
└── test_scheduler.py

📝 Modified Files:
├── requirements.txt (+ APScheduler, pytz, tzlocal)
├── main.py (+ scheduler startup/shutdown)
├── src/crud/event_participation_crud.py (+ 3 functions)
└── src/api/endpoints/participations.py (+ 3 endpoints)
```

## ✅ เสร็จสมบูรณ์!

ระบบพร้อมใช้งานแล้ว! 🎉
