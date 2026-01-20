# API Guide: อัพโหลดและเรียกใช้รูปภาพ (Image Upload & Retrieval)

## 📋 ภาพรวม

ระบบจัดการรูปภาพสำหรับ:
- **รูป Banner กิจกรรม** (events)
- **รูปหลักฐานการวิ่ง** (proofs)
- **รูป Badge รางวัล** (rewards)

รูปทุกรูปจะถูกบันทึกลงฐานข้อมูลพร้อมข้อมูล metadata และ perceptual hash สำหรับตรวจจับรูปซ้ำ

---

## 🔑 Base URL

```
http://localhost:8001/api
```

---

## 📤 อัพโหลดรูปภาพ

### Endpoint
```
POST /api/images/upload
```

### Headers
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

### Request Body (Form Data)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | ไฟล์รูปภาพ (.jpg, .jpeg, .png, .heic, .webp) |
| `subfolder` | String | ❌ | หมวดหมู่: `events`, `proofs`, `rewards` (default: `events`) |

### Response
```json
{
  "success": true,
  "url": "/uploads/events/abc123def456.jpg",
  "image_hash": "0123456789abcdef",
  "image_id": 42,
  "message": "Image uploaded successfully"
}
```

### Example (JavaScript/React)

```javascript
// อัพโหลดรูปภาพ
async function uploadImage(file, category = 'events') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subfolder', category);

  const response = await fetch('http://localhost:8001/api/images/upload', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`
    },
    body: formData
  });

  const result = await response.json();
  
  if (result.success) {
    console.log('Upload success:', result.url);
    console.log('Image ID:', result.image_id);
    return result;
  } else {
    throw new Error(result.error);
  }
}

// ตัวอย่างการใช้งาน
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  try {
    const result = await uploadImage(file, 'events');
    setImageUrl(result.url); // เก็บ URL สำหรับแสดงผล
    setImageId(result.image_id); // เก็บ ID สำหรับบันทึกลง event/reward
  } catch (error) {
    console.error('Upload failed:', error);
  }
};
```

### Example (Axios)

```javascript
import axios from 'axios';

const uploadImage = async (file, category = 'events') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subfolder', category);

  try {
    const response = await axios.post(
      'http://localhost:8001/api/images/upload',
      formData,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  } catch (error) {
    console.error('Upload error:', error.response?.data);
    throw error;
  }
};
```

---

## 🖼️ แสดงรูปภาพ

### วิธีที่ 1: แสดงผ่าน URL โดยตรง

```html
<!-- URL ที่ได้จาก response -->
<img src="http://localhost:8001/uploads/events/abc123def456.jpg" alt="Event Banner" />
```

```javascript
// React
function EventBanner({ imageUrl }) {
  const fullUrl = `http://localhost:8001${imageUrl}`;
  return <img src={fullUrl} alt="Event" className="banner" />;
}
```

### วิธีที่ 2: ใช้ Image Component

```jsx
// React Component สำหรับแสดงรูป
import React from 'react';

const ImageDisplay = ({ imagePath, alt = "Image", className = "" }) => {
  const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
  const imageUrl = imagePath ? `${baseUrl}${imagePath}` : '/placeholder.png';
  
  return (
    <img 
      src={imageUrl} 
      alt={alt} 
      className={className}
      onError={(e) => {
        e.target.src = '/placeholder.png'; // Fallback image
      }}
    />
  );
};

export default ImageDisplay;

// ใช้งาน
<ImageDisplay 
  imagePath="/uploads/events/abc123.jpg" 
  alt="Event Banner"
  className="w-full h-64 object-cover"
/>
```

---

## 📋 ดูรายการรูปภาพทั้งหมด

### Endpoint
```
GET /api/images/list
```

### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `category` | String | ❌ | - | กรองตามหมวดหมู่ (events/proofs/rewards) |
| `skip` | Integer | ❌ | 0 | จำนวนที่ข้าม (pagination) |
| `limit` | Integer | ❌ | 50 | จำนวนสูงสุด (1-100) |

### Response
```json
{
  "total": 150,
  "images": [
    {
      "id": 42,
      "filename": "abc123def456.jpg",
      "original_filename": "my-event-banner.jpg",
      "file_path": "/uploads/events/abc123def456.jpg",
      "category": "events",
      "file_size": 245678,
      "mime_type": "image/jpeg",
      "image_hash": "0123456789abcdef",
      "uploaded_by": 5,
      "created_at": "2026-01-14T10:30:00Z",
      "updated_at": "2026-01-14T10:30:00Z"
    }
  ]
}
```

### Example

```javascript
// ดูรายการรูปทั้งหมด
const fetchImages = async (category = null, page = 0, limit = 50) => {
  const params = new URLSearchParams({
    skip: page * limit,
    limit: limit
  });
  
  if (category) {
    params.append('category', category);
  }

  const response = await fetch(
    `http://localhost:8001/api/images/list?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );

  return await response.json();
};

// ใช้งาน
const images = await fetchImages('events', 0, 20);
console.log(`Total images: ${images.total}`);
```

---

## 👤 ดูรูปที่ตัวเองอัพโหลด

### Endpoint
```
GET /api/images/my-uploads
```

### Query Parameters
| Parameter | Type | Default |
|-----------|------|---------|
| `skip` | Integer | 0 |
| `limit` | Integer | 50 |

### Example

```javascript
const fetchMyUploads = async () => {
  const response = await fetch(
    'http://localhost:8001/api/images/my-uploads',
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

---

## 🔍 ดูรายละเอียดรูปภาพ

### Endpoint
```
GET /api/images/{image_id}
```

### Response
```json
{
  "id": 42,
  "filename": "abc123def456.jpg",
  "original_filename": "my-event-banner.jpg",
  "file_path": "/uploads/events/abc123def456.jpg",
  "category": "events",
  "file_size": 245678,
  "mime_type": "image/jpeg",
  "image_hash": "0123456789abcdef",
  "uploaded_by": 5,
  "created_at": "2026-01-14T10:30:00Z",
  "updated_at": "2026-01-14T10:30:00Z",
  "uploader": {
    "id": 5,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

---

## 🗑️ ลบรูปภาพ

### วิธีที่ 1: ลบด้วย Image ID (แนะนำ)

```
DELETE /api/images/{image_id}
```

### วิธีที่ 2: ลบด้วย File Path

```
DELETE /api/images/delete?file_path=/uploads/events/abc123.jpg
```

### Example

```javascript
const deleteImage = async (imageId) => {
  const response = await fetch(
    `http://localhost:8001/api/images/${imageId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  const result = await response.json();
  if (result.success) {
    console.log('Image deleted successfully');
  }
};
```

---

## ℹ️ ดูข้อมูลการตั้งค่า

### Endpoint
```
GET /api/images/info
```

### Response
```json
{
  "max_file_size_mb": 5,
  "allowed_extensions": [".jpg", ".jpeg", ".png", ".heic", ".webp"],
  "allowed_subfolders": ["events", "proofs", "rewards"],
  "upload_permissions": {
    "events": ["organizer", "staff"],
    "proofs": ["student", "officer", "staff", "organizer"],
    "rewards": ["organizer"]
  }
}
```

---

## 🎨 ตัวอย่าง Component สำหรับ Frontend

### 1. Image Upload Component (React)

```jsx
import React, { useState } from 'react';
import axios from 'axios';

const ImageUploader = ({ category = 'events', onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);

    // Upload
    await uploadFile(file);
  };

  const uploadFile = async (file) => {
    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('subfolder', category);

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/images/upload`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      if (response.data.success) {
        onUploadSuccess(response.data);
      } else {
        setError(response.data.error);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="image-uploader">
      <input
        type="file"
        accept=".jpg,.jpeg,.png,.heic,.webp"
        onChange={handleFileChange}
        disabled={uploading}
        className="file-input"
      />

      {preview && (
        <div className="preview">
          <img src={preview} alt="Preview" style={{ maxWidth: '300px' }} />
        </div>
      )}

      {uploading && <p>Uploading...</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
};

export default ImageUploader;
```

### 2. Image Gallery Component

```jsx
import React, { useEffect, useState } from 'react';

const ImageGallery = ({ category }) => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchImages();
  }, [category]);

  const fetchImages = async () => {
    try {
      const params = category ? `?category=${category}` : '';
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/images/list${params}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      const data = await response.json();
      setImages(data.images);
    } catch (error) {
      console.error('Failed to fetch images:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteImage = async (imageId) => {
    if (!confirm('Delete this image?')) return;

    try {
      await fetch(
        `${process.env.REACT_APP_API_URL}/api/images/${imageId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      fetchImages(); // Refresh
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      {images.map((image) => (
        <div key={image.id} className="relative">
          <img
            src={`${process.env.REACT_APP_API_URL}${image.file_path}`}
            alt={image.original_filename}
            className="w-full h-48 object-cover rounded"
          />
          <button
            onClick={() => deleteImage(image.id)}
            className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded"
          >
            Delete
          </button>
          <p className="text-sm mt-2">{image.original_filename}</p>
        </div>
      ))}
    </div>
  );
};

export default ImageGallery;
```

### 3. Drag & Drop Upload

```jsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const DragDropUploader = ({ category = 'events', onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('subfolder', category);

    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/api/images/upload`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        }
      );

      const data = await response.json();
      if (data.success) {
        onUploadSuccess(data);
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  }, [category, onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp']
    },
    maxSize: 5 * 1024 * 1024, // 5MB
    multiple: false
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed p-8 text-center cursor-pointer
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
        ${uploading ? 'opacity-50' : ''}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <p>Uploading...</p>
      ) : isDragActive ? (
        <p>Drop the image here...</p>
      ) : (
        <p>Drag & drop an image, or click to select</p>
      )}
    </div>
  );
};

export default DragDropUploader;
```

---

## 🔐 สิทธิ์การใช้งาน

| Category | อัพโหลด | ดู | ลบ |
|----------|---------|-----|-----|
| **events** | Staff, Organizer | ทุกคน (login) | Staff, Organizer |
| **proofs** | ทุกคน (login) | ทุกคน (login) | Staff, Organizer |
| **rewards** | Organizer | ทุกคน (login) | Organizer |

---

## ⚠️ ข้อจำกัดและข้อควรระวัง

1. **ขนาดไฟล์สูงสุด**: 5MB
2. **รูปแบบไฟล์**: `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`
3. **การเก็บไฟล์**: ไฟล์จะถูกเก็บที่ `/uploads/{category}/` พร้อมชื่อไฟล์ UUID
4. **Duplicate Detection**: ระบบมี perceptual hash เพื่อตรวจจับรูปซ้ำ
5. **CORS**: ตรวจสอบว่า frontend URL ได้รับอนุญาตใน `ALLOWED_ORIGINS`

---

## 🌐 Environment Variables (.env)

```env
# Frontend
REACT_APP_API_URL=http://localhost:8001

# Backend
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
```

---

## 📱 ตัวอย่างการใช้ใน Form สร้าง Event

```jsx
const CreateEventForm = () => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    banner_image_url: null,
    // ... other fields
  });

  const handleImageUpload = (uploadResult) => {
    setFormData({
      ...formData,
      banner_image_url: uploadResult.url
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // ส่งข้อมูล event พร้อม banner_image_url
    await fetch(`${API_URL}/api/events`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={formData.title}
        onChange={(e) => setFormData({...formData, title: e.target.value})}
        placeholder="Event Title"
      />

      {/* Image Upload */}
      <ImageUploader 
        category="events"
        onUploadSuccess={handleImageUpload}
      />

      {/* Preview uploaded image */}
      {formData.banner_image_url && (
        <img 
          src={`${API_URL}${formData.banner_image_url}`}
          alt="Banner Preview"
          className="w-full h-64 object-cover"
        />
      )}

      <button type="submit">Create Event</button>
    </form>
  );
};
```

---

## 🎯 Best Practices

1. **แสดง Loading State** ระหว่างอัพโหลด
2. **แสดง Preview** ก่อนอัพโหลดจริง
3. **Validate ขนาดไฟล์** ก่อนอัพโหลด (client-side)
4. **จัดการ Error** ให้ชัดเจน
5. **ใช้ Placeholder** เมื่อรูปโหลดไม่สำเร็จ
6. **Optimize รูป** ก่อนอัพโหลด (ถ้าจำเป็น)
7. **เก็บ Image URL** ไว้ใน state/database สำหรับแสดงผลภายหลัง

---

## 🐛 Troubleshooting

### รูปไม่แสดง
- ตรวจสอบ CORS settings
- ตรวจสอบว่า static files mount ถูกต้อง: `/api/uploads`
- ตรวจสอบ path ว่าถูกต้อง

### อัพโหลดไม่สำเร็จ
- ตรวจสอบ token ยังไม่หมดอายุ
- ตรวจสอบสิทธิ์ผู้ใช้
- ตรวจสอบขนาดและรูปแบบไฟล์

### 403 Forbidden
- ตรวจสอบสิทธิ์ตามหมวดหมู่รูปภาพ
- events/rewards ต้องเป็น staff/organizer
