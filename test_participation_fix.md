# แก้ไขปัญหา: ไม่สามารถสมัครกิจกรรมใหม่ได้หลังจากยกเลิก

## ปัญหาเดิม
1. User สมัครกิจกรรม → status = "joined" ✅
2. User ยกเลิกกิจกรรม → status = "cancelled" ✅
3. User พยายามสมัครใหม่ → สร้าง record ใหม่แทนที่จะอัปเดต record เดิม ❌

## สาเหตุ
- ฟังก์ชัน `create_participation()` ไม่มีการตรวจสอบว่า user มี participation ที่ยกเลิกไปแล้วหรือไม่
- ทุกครั้งที่สมัครจะสร้าง record ใหม่เสมอ ทำให้มีหลาย records สำหรับ user คนเดียวกัน

## วิธีแก้ไข
แก้ไขไฟล์: `src/crud/event_participation_crud.py`

### การทำงานใหม่:
1. **ตรวจสอบ participation ที่มีอยู่แล้ว**: ค้นหา participation ของ user สำหรับกิจกรรมนี้
2. **ป้องกันการสมัครซ้ำ**: ถ้ามี participation ที่ active (ไม่ใช่ cancelled) แล้ว → return error
3. **Reactivate record เดิม**: ถ้ามีแค่ record ที่ cancelled → อัปเดต record เดิมเป็น "joined" แทนการสร้างใหม่
4. **สร้าง record ใหม่**: ถ้าไม่มี record เลย → สร้างใหม่ตามปกติ

### ข้อดี:
- ✅ ป้องกันการมี multiple records ที่ active สำหรับ user คนเดียวกัน
- ✅ ลดความซับซ้อนของ database (ไม่มี participation หลาย records ต่อ user)
- ✅ รักษา history โดยการ reuse record เดิม
- ✅ Generate join code ใหม่ทุกครั้งที่สมัครใหม่

## การทดสอบ
1. User สมัครกิจกรรม → ควรได้ record ใหม่ status = "joined"
2. User ยกเลิก → ควร update record เป็น status = "cancelled"
3. User สมัครใหม่ → ควร reactivate record เดิมเป็น status = "joined" (ไม่สร้างใหม่)
4. User พยายามสมัครอีกครั้ง (ขณะที่ status = "joined") → ควรได้ error "คุณได้สมัครกิจกรรมนี้แล้ว"

## API Response ที่คาดหวัง

### กรณีที่ 1: สมัครครั้งแรก
```json
{
  "id": 1,
  "user_id": 3,
  "event_id": 5,
  "status": "joined",
  "join_code": "12345"
}
```

### กรณีที่ 2: ยกเลิก
```json
{
  "id": 1,
  "user_id": 3,
  "event_id": 5,
  "status": "cancelled",
  "cancellation_reason": "ไม่สะดวก"
}
```

### กรณีที่ 3: สมัครใหม่หลังยกเลิก (Reactivate)
```json
{
  "id": 1,  // Same ID
  "user_id": 3,
  "event_id": 5,
  "status": "joined",
  "join_code": "67890",  // New code
  "cancellation_reason": null,
  "cancelled_at": null
}
```

### กรณีที่ 4: พยายามสมัครซ้ำ (Error)
```json
{
  "detail": "คุณได้สมัครกิจกรรมนี้แล้ว"
}
```
