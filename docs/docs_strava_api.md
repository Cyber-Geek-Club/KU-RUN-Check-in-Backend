# API Guide: Strava Parser

## 📋 ภาพรวม

API สำหรับดึงข้อมูลระยะทางและข้อมูลกิจกรรมจาก Strava Activity Link

รองรับทั้ง:
- **Short links**: `https://strava.app.link/xxxxx`
- **Full URLs**: `https://www.strava.com/activities/xxxxx`

---

## 🔑 Base URL

```
http://localhost:8001/api
```

---

## 📡 Parse Strava Activity

### Endpoint
```
POST /api/strava/parse
```

### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request Body
```json
{
  "url": "https://strava.app.link/i1I3oE8wmZb"
}
```

### Response (Success)
```json
{
  "success": true,
  "distance_km": 1.1,
  "moving_time": "00:08:30",
  "activity_name": "Morning Run",
  "elevation_gain": "15 m"
}
```

### Response (Failed)
```json
{
  "success": false,
  "error": "Could not extract distance",
  "hint": "Please enter distance manually"
}
```

---

## 🚀 ตัวอย่างการใช้งาน

### JavaScript (Fetch)

```javascript
async function parseStravaActivity(stravaUrl) {
  const response = await fetch('http://localhost:8001/api/strava/parse', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ url: stravaUrl })
  });

  const result = await response.json();
  
  if (result.success) {
    console.log('Distance:', result.distance_km, 'km');
    console.log('Time:', result.moving_time);
    console.log('Activity:', result.activity_name);
    return result;
  } else {
    console.warn('Parse failed:', result.error);
    console.log('Hint:', result.hint);
    return null;
  }
}

// Usage
const activity = await parseStravaActivity('https://strava.app.link/i1I3oE8wmZb');
if (activity) {
  setDistance(activity.distance_km);
}
```

### Axios

```javascript
import axios from 'axios';

const parseStrava = async (stravaUrl) => {
  try {
    const response = await axios.post(
      `${process.env.REACT_APP_API_URL}/api/strava/parse`,
      { url: stravaUrl },
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Strava parse error:', error.response?.data);
    return { success: false, error: 'Network error' };
  }
};
```

### React Component Example

```jsx
import React, { useState } from 'react';

const StravaInput = ({ onDistanceExtracted }) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleParse = async () => {
    if (!url.includes('strava')) {
      setError('Please enter a valid Strava link');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/strava/parse', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url })
      });

      const result = await response.json();

      if (result.success) {
        onDistanceExtracted({
          distance: result.distance_km,
          time: result.moving_time,
          name: result.activity_name
        });
      } else {
        setError(result.hint || result.error);
      }
    } catch (err) {
      setError('Failed to parse Strava link');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strava-input">
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste Strava activity link"
        className="input"
      />
      <button 
        onClick={handleParse} 
        disabled={loading || !url}
        className="btn"
      >
        {loading ? 'Parsing...' : 'Get Distance'}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
};

export default StravaInput;
```

---

## ✅ Test Cases

| Input URL | Expected Result |
|-----------|-----------------|
| `https://strava.app.link/i1I3oE8wmZb` | ✅ ดึงระยะทาง + เวลา |
| `https://www.strava.com/activities/16830167117` | ✅ ดึงระยะทาง + เวลา |
| `https://strava.com/activities/12345678` | ✅ ดึงระยะทาง + เวลา |
| `https://google.com` | ❌ `success: false` (Invalid URL) |
| `invalid-url` | ❌ `success: false` (Invalid URL) |

---

## 📊 Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | การ parse สำเร็จหรือไม่ |
| `distance_km` | float | ระยะทางเป็นกิโลเมตร (ทศนิยม 2 ตำแหน่ง) |
| `moving_time` | string | เวลาวิ่งในรูปแบบ `HH:MM:SS` |
| `activity_name` | string | ชื่อกิจกรรม |
| `elevation_gain` | string | ความสูงที่เพิ่มขึ้น (เช่น `"15 m"`) |
| `error` | string | ข้อความ error (กรณี `success: false`) |
| `hint` | string | คำแนะนำสำหรับผู้ใช้ (กรณี `success: false`) |

---

## ⚠️ ข้อควรระวัง

1. **ต้องมี Authentication** - ต้องส่ง Bearer token
2. **Timeout**: 10 วินาที - ถ้า Strava ตอบช้า จะ timeout
3. **Rate Limiting**: ไม่มีจาก API เรา แต่ Strava อาจ block ถ้าเรียกถี่เกินไป
4. **Private Activities**: Activities ที่ตั้งเป็น private อาจไม่สามารถดึงข้อมูลได้

---

## 🔐 สิทธิ์การใช้งาน

| Action | Permission |
|--------|------------|
| Parse Strava URL | ทุกคนที่ login แล้ว |

---

## 🐛 Troubleshooting

### "Could not extract distance"
- Strava activity อาจเป็น private
- Link อาจหมดอายุหรือถูกลบ
- **แนะนำ:** ให้ผู้ใช้กรอกระยะทางเอง

### "Invalid Strava URL format"
- URL ไม่ใช่ format ของ Strava
- ตรวจสอบว่า copy link มาถูกต้อง

### "Request timeout"
- Strava server ตอบช้า
- ลองใหม่อีกครั้ง หรือกรอกระยะทางเอง
