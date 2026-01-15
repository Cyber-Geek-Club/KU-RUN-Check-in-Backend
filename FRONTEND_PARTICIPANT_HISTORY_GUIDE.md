# 📱 คู่มือ Frontend: เรียก API ประวัติผู้เข้าร่วมกิจกรรม (Participant Snapshots)

## 🎯 สิ่งที่ API ตัวนี้ทำได้

ระบบ Participant Snapshots จะช่วยให้คุณ:
- ✅ **ดูจำนวนคนเข้าร่วม** - รู้ว่าในแต่ละช่วงเวลามีคนเข้าร่วมกี่คน
- ✅ **ดูรายชื่อผู้เข้าร่วม** - รู้ว่ามีใครบ้างในกิจกรรม
- ✅ **ดูสถานะของแต่ละคน** - รู้ว่าแต่ละคนอยู่สถานะไหน (joined, checked_in, completed, cancelled)
- ✅ **ดูข้อมูลย้อนหลัง** - ดูประวัติแบบ snapshot ในช่วงเวลาต่างๆ

---

## 🔑 Authentication

ทุก API ต้องส่ง **Bearer Token** ใน Header:

```typescript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

**สิทธิ์:** ต้องเป็น **Staff หรือ Organizer** เท่านั้น

---

## 📚 API Endpoints

### 1. ดูรายการ Snapshots ทั้งหมดของ Event

**GET** `/api/events/{eventId}/participants/history`

ใช้เพื่อ: **ดูว่ามี snapshot อะไรบ้างของ event นี้**

#### Request Parameters:

```typescript
{
  eventId: number,           // ID ของ event (ใน URL)
  page?: number,             // หน้าที่ต้องการ (default: 1)
  page_size?: number         // จำนวนรายการต่อหน้า (default: 20, max: 100)
}
```

#### Response:

```typescript
{
  total: number,                    // จำนวน snapshots ทั้งหมด
  page: number,                     // หน้าปัจจุบัน
  page_size: number,                // จำนวนรายการต่อหน้า
  total_pages: number,              // จำนวนหน้าทั้งหมด
  snapshots: [
    {
      id: number,                   // ID ของ snapshot (internal)
      snapshot_id: string,          // UUID ของ snapshot (ใช้อันนี้เรียก entries)
      snapshot_time: string,        // เวลาที่สร้าง snapshot (ISO 8601)
      entry_count: number,          // จำนวนคนในช่วงเวลานั้น
      description: string | null    // คำอธิบาย (ถ้ามี)
    }
  ]
}
```

#### ตัวอย่าง Code (TypeScript/React):

```typescript
interface Snapshot {
  id: number;
  snapshot_id: string;
  snapshot_time: string;
  entry_count: number;
  description: string | null;
}

interface SnapshotListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  snapshots: Snapshot[];
}

// ฟังก์ชันดึง snapshots
async function fetchSnapshotHistory(
  eventId: number, 
  page: number = 1, 
  pageSize: number = 20
): Promise<SnapshotListResponse> {
  const response = await fetch(
    `/api/events/${eventId}/participants/history?page=${page}&page_size=${pageSize}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch snapshots');
  }
  
  return await response.json();
}

// ใช้งาน
const data = await fetchSnapshotHistory(11, 1, 20);
console.log(`จำนวน snapshots ทั้งหมด: ${data.total}`);
console.log(`Snapshot แรก มีคนเข้าร่วม: ${data.snapshots[0]?.entry_count} คน`);
```

#### แสดงผลใน UI:

```tsx
function SnapshotHistoryList({ eventId }: { eventId: number }) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    async function loadSnapshots() {
      setLoading(true);
      try {
        const data = await fetchSnapshotHistory(eventId, page, 20);
        setSnapshots(data.snapshots);
        setTotalPages(data.total_pages);
      } catch (error) {
        console.error('Error loading snapshots:', error);
      } finally {
        setLoading(false);
      }
    }
    loadSnapshots();
  }, [eventId, page]);

  if (loading) return <div>กำลังโหลด...</div>;

  return (
    <div>
      <h2>ประวัติ Snapshots</h2>
      <table>
        <thead>
          <tr>
            <th>เวลา</th>
            <th>จำนวนคน</th>
            <th>คำอธิบาย</th>
            <th>ดูรายละเอียด</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((snapshot) => (
            <tr key={snapshot.snapshot_id}>
              <td>{new Date(snapshot.snapshot_time).toLocaleString('th-TH')}</td>
              <td>{snapshot.entry_count} คน</td>
              <td>{snapshot.description || '-'}</td>
              <td>
                <button onClick={() => viewDetails(snapshot.snapshot_id)}>
                  ดูรายชื่อ
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Pagination */}
      <div>
        <button 
          disabled={page === 1} 
          onClick={() => setPage(page - 1)}
        >
          ก่อนหน้า
        </button>
        <span>หน้า {page} / {totalPages}</span>
        <button 
          disabled={page === totalPages} 
          onClick={() => setPage(page + 1)}
        >
          ถัดไป
        </button>
      </div>
    </div>
  );
}
```

---

### 2. ดูรายชื่อผู้เข้าร่วมใน Snapshot

**GET** `/api/events/{eventId}/participants/history/{snapshotId}/entries`

ใช้เพื่อ: **ดูรายชื่อและสถานะของคนที่เข้าร่วมในช่วงเวลานั้นๆ**

#### Request Parameters:

```typescript
{
  eventId: number,              // ID ของ event (ใน URL)
  snapshotId: string,           // UUID ของ snapshot (ใน URL)
  page?: number,                // หน้าที่ต้องการ (default: 1)
  page_size?: number            // จำนวนรายการต่อหน้า (default: 50, max: 200)
}
```

#### Response:

```typescript
{
  snapshot_id: string,              // UUID ของ snapshot
  snapshot_time: string,            // เวลาที่สร้าง snapshot
  total_entries: number,            // จำนวนคนทั้งหมด
  page: number,                     // หน้าปัจจุบัน
  page_size: number,                // จำนวนรายการต่อหน้า
  total_pages: number,              // จำนวนหน้าทั้งหมด
  entries: [
    {
      id: number,                   // ID ของ entry (internal)
      entry_id: string,             // UUID ของ entry (unique key สำหรับแสดงผล)
      snapshot_id: number,          // ID ของ snapshot
      participation_id: number | null, // ID ของ participation record
      user_id: number,              // ID ของผู้ใช้
      user_name: string,            // ชื่อผู้ใช้
      user_email: string | null,    // อีเมลผู้ใช้
      action: string,               // การกระทำล่าสุด (joined, checked_in, completed, cancelled)
      status: string,               // สถานะปัจจุบัน (joined, checked_in, completed, cancelled)
      created_at: string,           // เวลาที่สร้าง entry (ISO 8601)
      joined_at: string | null,     // เวลาที่เข้าร่วม
      checked_in_at: string | null, // เวลาที่เช็คอิน
      completed_at: string | null,  // เวลาที่เสร็จสิ้น
      metadata: object | null       // ข้อมูลเพิ่มเติม (join_code, checkin_date, proof_image_url, etc.)
    }
  ]
}
```

#### ตัวอย่าง Code (TypeScript/React):

```typescript
interface ParticipantEntry {
  id: number;
  entry_id: string;
  snapshot_id: number;
  participation_id: number | null;
  user_id: number;
  user_name: string;
  user_email: string | null;
  action: string;
  status: string;
  created_at: string;
  joined_at: string | null;
  checked_in_at: string | null;
  completed_at: string | null;
  metadata: any | null;
}

interface SnapshotEntriesResponse {
  snapshot_id: string;
  snapshot_time: string;
  total_entries: number;
  page: number;
  page_size: number;
  total_pages: number;
  entries: ParticipantEntry[];
}

// ฟังก์ชันดึงรายชื่อผู้เข้าร่วม
async function fetchSnapshotEntries(
  eventId: number,
  snapshotId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<SnapshotEntriesResponse> {
  const response = await fetch(
    `/api/events/${eventId}/participants/history/${snapshotId}/entries?page=${page}&page_size=${pageSize}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch entries');
  }
  
  return await response.json();
}

// ใช้งาน
const data = await fetchSnapshotEntries(11, '550e8400-e29b-41d4-a716-446655440000', 1, 50);
console.log(`จำนวนคนทั้งหมด: ${data.total_entries}`);
console.log(`คนแรก: ${data.entries[0]?.user_name} - สถานะ: ${data.entries[0]?.status}`);
```

#### แสดงผลใน UI:

```tsx
function ParticipantList({ eventId, snapshotId }: { eventId: number; snapshotId: string }) {
  const [entries, setEntries] = useState<ParticipantEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalEntries, setTotalEntries] = useState(0);
  const [snapshotTime, setSnapshotTime] = useState('');

  useEffect(() => {
    async function loadEntries() {
      setLoading(true);
      try {
        const data = await fetchSnapshotEntries(eventId, snapshotId, page, 50);
        setEntries(data.entries);
        setTotalPages(data.total_pages);
        setTotalEntries(data.total_entries);
        setSnapshotTime(data.snapshot_time);
      } catch (error) {
        console.error('Error loading entries:', error);
      } finally {
        setLoading(false);
      }
    }
    loadEntries();
  }, [eventId, snapshotId, page]);

  // ฟังก์ชันแปลงสถานะเป็นภาษาไทย
  const getStatusLabel = (status: string) => {
    const statusMap: Record<string, string> = {
      'joined': 'เข้าร่วม',
      'checked_in': 'เช็คอินแล้ว',
      'completed': 'เสร็จสิ้น',
      'cancelled': 'ยกเลิก'
    };
    return statusMap[status] || status;
  };

  // ฟังก์ชันเลือกสีตามสถานะ
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      'joined': 'blue',
      'checked_in': 'orange',
      'completed': 'green',
      'cancelled': 'red'
    };
    return colorMap[status] || 'gray';
  };

  if (loading) return <div>กำลังโหลด...</div>;

  return (
    <div>
      <h2>รายชื่อผู้เข้าร่วม</h2>
      <p>เวลา: {new Date(snapshotTime).toLocaleString('th-TH')}</p>
      <p>จำนวนทั้งหมด: {totalEntries} คน</p>
      
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>ชื่อ</th>
            <th>อีเมล</th>
            <th>สถานะ</th>
            <th>เวลาเข้าร่วม</th>
            <th>เวลาเช็คอิน</th>
            <th>เวลาเสร็จสิ้น</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => (
            <tr key={entry.entry_id}>
              <td>{(page - 1) * 50 + index + 1}</td>
              <td>{entry.user_name}</td>
              <td>{entry.user_email || '-'}</td>
              <td>
                <span style={{ 
                  color: getStatusColor(entry.status),
                  fontWeight: 'bold' 
                }}>
                  {getStatusLabel(entry.status)}
                </span>
              </td>
              <td>
                {entry.joined_at 
                  ? new Date(entry.joined_at).toLocaleString('th-TH')
                  : '-'
                }
              </td>
              <td>
                {entry.checked_in_at 
                  ? new Date(entry.checked_in_at).toLocaleString('th-TH')
                  : '-'
                }
              </td>
              <td>
                {entry.completed_at 
                  ? new Date(entry.completed_at).toLocaleString('th-TH')
                  : '-'
                }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Pagination */}
      <div>
        <button 
          disabled={page === 1} 
          onClick={() => setPage(page - 1)}
        >
          ก่อนหน้า
        </button>
        <span>หน้า {page} / {totalPages}</span>
        <button 
          disabled={page === totalPages} 
          onClick={() => setPage(page + 1)}
        >
          ถัดไป
        </button>
      </div>
    </div>
  );
}
```

---

### 3. สร้าง Snapshot ใหม่

**POST** `/api/events/{eventId}/participants/snapshots`

ใช้เพื่อ: **บันทึกภาพรวมของผู้เข้าร่วม ณ เวลานั้นๆ**

#### Request Parameters:

```typescript
{
  eventId: number,                // ID ของ event (ใน URL)
  description?: string            // คำอธิบาย snapshot (Query parameter, optional)
}
```

#### Response:

```typescript
{
  id: number,                     // ID ของ snapshot (internal)
  snapshot_id: string,            // UUID ของ snapshot
  event_id: number,               // ID ของ event
  snapshot_time: string,          // เวลาที่สร้าง
  entry_count: number,            // จำนวนคนที่บันทึก
  created_by: number | null,      // User ID ผู้สร้าง
  description: string | null      // คำอธิบาย
}
```

#### ตัวอย่าง Code:

```typescript
async function createSnapshot(
  eventId: number,
  description?: string
): Promise<Snapshot> {
  const url = description
    ? `/api/events/${eventId}/participants/snapshots?description=${encodeURIComponent(description)}`
    : `/api/events/${eventId}/participants/snapshots`;
    
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to create snapshot');
  }
  
  return await response.json();
}

// ใช้งาน
const newSnapshot = await createSnapshot(11, 'End of day snapshot');
console.log(`สร้าง snapshot สำเร็จ! มีคนเข้าร่วม ${newSnapshot.entry_count} คน`);
```

#### ตัวอย่าง UI:

```tsx
function CreateSnapshotButton({ eventId }: { eventId: number }) {
  const [loading, setLoading] = useState(false);
  const [description, setDescription] = useState('');

  const handleCreateSnapshot = async () => {
    if (loading) return;
    
    setLoading(true);
    try {
      const snapshot = await createSnapshot(eventId, description);
      alert(`สร้าง snapshot สำเร็จ! บันทึกข้อมูล ${snapshot.entry_count} คน`);
      setDescription('');
      // รีเฟรชรายการ snapshots
    } catch (error) {
      alert('เกิดข้อผิดพลาดในการสร้าง snapshot');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="คำอธิบาย (ไม่บังคับ)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <button 
        onClick={handleCreateSnapshot}
        disabled={loading}
      >
        {loading ? 'กำลังสร้าง...' : '📸 บันทึก Snapshot'}
      </button>
    </div>
  );
}
```

---

### 4. ลบ Snapshot

**DELETE** `/api/events/{eventId}/participants/history/{snapshotId}`

ใช้เพื่อ: **ลบ snapshot (และ entries ทั้งหมด)**

#### Request Parameters:

```typescript
{
  eventId: number,              // ID ของ event (ใน URL)
  snapshotId: string            // UUID ของ snapshot (ใน URL)
}
```

#### Response:

`204 No Content` (ไม่มี body)

#### ตัวอย่าง Code:

```typescript
async function deleteSnapshot(
  eventId: number,
  snapshotId: string
): Promise<void> {
  const response = await fetch(
    `/api/events/${eventId}/participants/history/${snapshotId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to delete snapshot');
  }
}

// ใช้งาน
await deleteSnapshot(11, '550e8400-e29b-41d4-a716-446655440000');
console.log('ลบ snapshot สำเร็จ');
```

#### ตัวอย่าง UI:

```tsx
function DeleteSnapshotButton({ 
  eventId, 
  snapshotId,
  onDeleted 
}: { 
  eventId: number;
  snapshotId: string;
  onDeleted: () => void;
}) {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!confirm('คุณแน่ใจหรือไม่ที่จะลบ snapshot นี้? (ไม่สามารถย้อนกลับได้)')) {
      return;
    }
    
    setLoading(true);
    try {
      await deleteSnapshot(eventId, snapshotId);
      alert('ลบ snapshot สำเร็จ');
      onDeleted();
    } catch (error) {
      alert('เกิดข้อผิดพลาดในการลบ snapshot');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button 
      onClick={handleDelete}
      disabled={loading}
      style={{ color: 'red' }}
    >
      {loading ? 'กำลังลบ...' : '🗑️ ลบ'}
    </button>
  );
}
```

---

## 📊 ตัวอย่าง Use Cases

### Use Case 1: แดชบอร์ดแสดงสถิติรายวัน

```tsx
function DailyStatsdashboard({ eventId }: { eventId: number }) {
  const [dailySnapshots, setDailySnapshots] = useState<Snapshot[]>([]);

  useEffect(() => {
    async function loadDailyStats() {
      const data = await fetchSnapshotHistory(eventId, 1, 30);
      setDailySnapshots(data.snapshots);
    }
    loadDailyStats();
  }, [eventId]);

  return (
    <div>
      <h2>สถิติรายวัน</h2>
      {dailySnapshots.map((snapshot) => (
        <div key={snapshot.snapshot_id}>
          <p>
            {new Date(snapshot.snapshot_time).toLocaleDateString('th-TH')}:
            <strong> {snapshot.entry_count} คน</strong>
          </p>
        </div>
      ))}
    </div>
  );
}
```

### Use Case 2: เปรียบเทียบจำนวนคนระหว่างช่วงเวลา

```tsx
function CompareSnapshots({ eventId }: { eventId: number }) {
  const [snapshot1, setSnapshot1] = useState<SnapshotEntriesResponse | null>(null);
  const [snapshot2, setSnapshot2] = useState<SnapshotEntriesResponse | null>(null);

  async function loadComparison(snapshotId1: string, snapshotId2: string) {
    const data1 = await fetchSnapshotEntries(eventId, snapshotId1);
    const data2 = await fetchSnapshotEntries(eventId, snapshotId2);
    setSnapshot1(data1);
    setSnapshot2(data2);
  }

  const difference = (snapshot2?.total_entries || 0) - (snapshot1?.total_entries || 0);

  return (
    <div>
      <h2>เปรียบเทียบ Snapshots</h2>
      {snapshot1 && snapshot2 && (
        <div>
          <p>Snapshot 1: {snapshot1.total_entries} คน</p>
          <p>Snapshot 2: {snapshot2.total_entries} คน</p>
          <p>
            ความแตกต่าง: 
            <strong style={{ color: difference > 0 ? 'green' : 'red' }}>
              {difference > 0 ? '+' : ''}{difference} คน
            </strong>
          </p>
        </div>
      )}
    </div>
  );
}
```

### Use Case 3: Export ข้อมูลเป็น CSV

```tsx
function ExportToCSV({ eventId, snapshotId }: { eventId: number; snapshotId: string }) {
  const exportToCSV = async () => {
    // ดึงข้อมูลทั้งหมด (อาจต้องดึงหลายหน้า)
    const allEntries: ParticipantEntry[] = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const data = await fetchSnapshotEntries(eventId, snapshotId, page, 200);
      allEntries.push(...data.entries);
      hasMore = page < data.total_pages;
      page++;
    }

    // แปลงเป็น CSV
    const csvHeader = 'ชื่อ,อีเมล,สถานะ,เวลาเข้าร่วม,เวลาเช็คอิน,เวลาเสร็จสิ้น\n';
    const csvRows = allEntries.map(entry => 
      `${entry.user_name},${entry.user_email || ''},${entry.status},` +
      `${entry.joined_at || ''},${entry.checked_in_at || ''},${entry.completed_at || ''}`
    ).join('\n');

    // ดาวน์โหลดไฟล์
    const blob = new Blob([csvHeader + csvRows], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `participants_${snapshotId}.csv`;
    link.click();
  };

  return (
    <button onClick={exportToCSV}>
      📥 Export เป็น CSV
    </button>
  );
}
```

### Use Case 4: แสดงสถิติแบบ Real-time

```tsx
function ParticipantStats({ eventId }: { eventId: number }) {
  const [stats, setStats] = useState({
    joined: 0,
    checked_in: 0,
    completed: 0,
    cancelled: 0
  });

  useEffect(() => {
    async function loadLatestStats() {
      // ดึง snapshot ล่าสุด
      const history = await fetchSnapshotHistory(eventId, 1, 1);
      if (history.snapshots.length === 0) return;

      const latestSnapshot = history.snapshots[0];
      const entries = await fetchSnapshotEntries(eventId, latestSnapshot.snapshot_id, 1, 1000);

      // นับสถานะ
      const statusCount = {
        joined: 0,
        checked_in: 0,
        completed: 0,
        cancelled: 0
      };

      entries.entries.forEach(entry => {
        if (entry.status in statusCount) {
          statusCount[entry.status as keyof typeof statusCount]++;
        }
      });

      setStats(statusCount);
    }

    loadLatestStats();
    // รีเฟรชทุก 5 นาที
    const interval = setInterval(loadLatestStats, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [eventId]);

  return (
    <div>
      <h2>สถิติผู้เข้าร่วม</h2>
      <div style={{ display: 'flex', gap: '20px' }}>
        <div style={{ color: 'blue' }}>
          <h3>{stats.joined}</h3>
          <p>เข้าร่วม</p>
        </div>
        <div style={{ color: 'orange' }}>
          <h3>{stats.checked_in}</h3>
          <p>เช็คอินแล้ว</p>
        </div>
        <div style={{ color: 'green' }}>
          <h3>{stats.completed}</h3>
          <p>เสร็จสิ้น</p>
        </div>
        <div style={{ color: 'red' }}>
          <h3>{stats.cancelled}</h3>
          <p>ยกเลิก</p>
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 Status แต่ละประเภท

| Status | ความหมาย | สีแนะนำ |
|--------|----------|---------|
| `joined` | เข้าร่วมกิจกรรมแล้ว (ยังไม่เช็คอิน) | 🔵 น้ำเงิน |
| `checked_in` | เช็คอินแล้ว (อยู่ในกิจกรรม) | 🟠 ส้ม |
| `completed` | เสร็จสิ้นกิจกรรม | 🟢 เขียว |
| `cancelled` | ยกเลิกการเข้าร่วม | 🔴 แดง |

---

## ⚠️ Error Handling

```typescript
async function fetchWithErrorHandling<T>(
  fetchFn: () => Promise<Response>
): Promise<T> {
  try {
    const response = await fetchFn();
    
    if (response.status === 401) {
      throw new Error('ไม่ได้รับอนุญาต - กรุณาเข้าสู่ระบบใหม่');
    }
    
    if (response.status === 403) {
      throw new Error('ไม่มีสิทธิ์เข้าถึง - ต้องเป็น Staff หรือ Organizer');
    }
    
    if (response.status === 404) {
      throw new Error('ไม่พบข้อมูล');
    }
    
    if (!response.ok) {
      throw new Error(`เกิดข้อผิดพลาด: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

---

## 💡 Tips & Best Practices

### 1. ใช้ Unique Key สำหรับ React List

```tsx
// ✅ ถูกต้อง - ใช้ entry_id
{entries.map(entry => (
  <tr key={entry.entry_id}>
    ...
  </tr>
))}

// ❌ ผิด - ใช้ index
{entries.map((entry, index) => (
  <tr key={index}>
    ...
  </tr>
))}
```

### 2. Cache ข้อมูลด้วย React Query

```typescript
import { useQuery } from '@tanstack/react-query';

function useSnapshotHistory(eventId: number, page: number) {
  return useQuery({
    queryKey: ['snapshots', eventId, page],
    queryFn: () => fetchSnapshotHistory(eventId, page),
    staleTime: 5 * 60 * 1000, // 5 นาที
  });
}
```

### 3. แสดง Loading State

```tsx
function ParticipantList() {
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState([]);

  if (loading) {
    return (
      <div>
        <Spinner />
        <p>กำลังโหลดข้อมูล...</p>
      </div>
    );
  }

  return <table>...</table>;
}
```

### 4. Handle Empty State

```tsx
if (entries.length === 0) {
  return (
    <div>
      <p>ยังไม่มีผู้เข้าร่วมในช่วงเวลานี้</p>
    </div>
  );
}
```

### 5. Pagination แบบ Infinite Scroll

```tsx
function InfiniteParticipantList({ eventId, snapshotId }: Props) {
  const [entries, setEntries] = useState<ParticipantEntry[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadMore = async () => {
    const data = await fetchSnapshotEntries(eventId, snapshotId, page, 50);
    setEntries(prev => [...prev, ...data.entries]);
    setHasMore(page < data.total_pages);
    setPage(page + 1);
  };

  return (
    <InfiniteScroll
      dataLength={entries.length}
      next={loadMore}
      hasMore={hasMore}
      loader={<h4>Loading...</h4>}
    >
      {entries.map(entry => (
        <ParticipantCard key={entry.entry_id} entry={entry} />
      ))}
    </InfiniteScroll>
  );
}
```

---

## 📱 ตัวอย่าง Complete Component

```tsx
import React, { useState, useEffect } from 'react';

interface ParticipantHistoryPageProps {
  eventId: number;
}

export function ParticipantHistoryPage({ eventId }: ParticipantHistoryPageProps) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const [entries, setEntries] = useState<ParticipantEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  // โหลด snapshots
  useEffect(() => {
    async function loadSnapshots() {
      setLoading(true);
      try {
        const data = await fetchSnapshotHistory(eventId, 1, 50);
        setSnapshots(data.snapshots);
      } catch (error) {
        console.error('Error loading snapshots:', error);
      } finally {
        setLoading(false);
      }
    }
    loadSnapshots();
  }, [eventId]);

  // โหลด entries เมื่อเลือก snapshot
  useEffect(() => {
    if (!selectedSnapshot) return;

    async function loadEntries() {
      setLoading(true);
      try {
        const data = await fetchSnapshotEntries(eventId, selectedSnapshot, page, 50);
        setEntries(data.entries);
        setTotalPages(data.total_pages);
      } catch (error) {
        console.error('Error loading entries:', error);
      } finally {
        setLoading(false);
      }
    }
    loadEntries();
  }, [eventId, selectedSnapshot, page]);

  // สร้าง snapshot ใหม่
  const handleCreateSnapshot = async () => {
    try {
      const newSnapshot = await createSnapshot(eventId, 'Manual snapshot');
      setSnapshots([newSnapshot, ...snapshots]);
      alert(`สร้าง snapshot สำเร็จ! บันทึก ${newSnapshot.entry_count} คน`);
    } catch (error) {
      alert('เกิดข้อผิดพลาด');
    }
  };

  if (loading && snapshots.length === 0) {
    return <div>กำลังโหลด...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <h1>ประวัติผู้เข้าร่วม - กิจกรรม #{eventId}</h1>
        <button onClick={handleCreateSnapshot}>
          📸 สร้าง Snapshot ใหม่
        </button>
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* รายการ Snapshots */}
        <div style={{ flex: 1 }}>
          <h2>รายการ Snapshots</h2>
          <ul>
            {snapshots.map(snapshot => (
              <li 
                key={snapshot.snapshot_id}
                onClick={() => setSelectedSnapshot(snapshot.snapshot_id)}
                style={{ 
                  cursor: 'pointer',
                  backgroundColor: selectedSnapshot === snapshot.snapshot_id ? '#e3f2fd' : 'white',
                  padding: '10px',
                  margin: '5px 0',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              >
                <div>
                  <strong>{new Date(snapshot.snapshot_time).toLocaleString('th-TH')}</strong>
                </div>
                <div>จำนวน: {snapshot.entry_count} คน</div>
                {snapshot.description && <div>หมายเหตุ: {snapshot.description}</div>}
              </li>
            ))}
          </ul>
        </div>

        {/* รายชื่อผู้เข้าร่วม */}
        <div style={{ flex: 2 }}>
          {selectedSnapshot ? (
            <>
              <h2>รายชื่อผู้เข้าร่วม</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f5f5f5' }}>
                    <th style={{ padding: '10px', border: '1px solid #ddd' }}>ชื่อ</th>
                    <th style={{ padding: '10px', border: '1px solid #ddd' }}>อีเมล</th>
                    <th style={{ padding: '10px', border: '1px solid #ddd' }}>สถานะ</th>
                    <th style={{ padding: '10px', border: '1px solid #ddd' }}>เวลาเช็คอิน</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(entry => (
                    <tr key={entry.entry_id}>
                      <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                        {entry.user_name}
                      </td>
                      <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                        {entry.user_email || '-'}
                      </td>
                      <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                        <span style={{ 
                          color: getStatusColor(entry.status),
                          fontWeight: 'bold'
                        }}>
                          {getStatusLabel(entry.status)}
                        </span>
                      </td>
                      <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                        {entry.checked_in_at 
                          ? new Date(entry.checked_in_at).toLocaleString('th-TH')
                          : '-'
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <button 
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  ← ก่อนหน้า
                </button>
                <span style={{ margin: '0 20px' }}>
                  หน้า {page} / {totalPages}
                </span>
                <button 
                  disabled={page === totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  ถัดไป →
                </button>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <p>กรุณาเลือก Snapshot เพื่อดูรายชื่อผู้เข้าร่วม</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper functions
function getStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    'joined': 'เข้าร่วม',
    'checked_in': 'เช็คอินแล้ว',
    'completed': 'เสร็จสิ้น',
    'cancelled': 'ยกเลิก'
  };
  return statusMap[status] || status;
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    'joined': '#2196F3',
    'checked_in': '#FF9800',
    'completed': '#4CAF50',
    'cancelled': '#F44336'
  };
  return colorMap[status] || '#757575';
}
```

---

## 🎉 สรุป

API นี้ช่วยให้คุณ:
- ✅ **ดูจำนวนคน** - จาก `entry_count` ใน snapshot
- ✅ **ดูรายชื่อ** - จาก `entries` array
- ✅ **ดูสถานะ** - จาก `status` field (joined, checked_in, completed, cancelled)
- ✅ **ดูย้อนหลัง** - จาก snapshot ในช่วงเวลาต่างๆ
- ✅ **สร้าง/ลบ Snapshot** - เก็บประวัติตามต้องการ

**Base URL:** `http://localhost:8001` (สำหรับ development)

**สิทธิ์:** ต้องเป็น **Staff หรือ Organizer** และส่ง **Bearer Token**

---

## 📞 ติดต่อสอบถาม

หากมีคำถามเพิ่มเติมหรือพบปัญหา กรุณาติดต่อทีม Backend หรือดูเอกสารเพิ่มเติมที่:
- `PARTICIPANT_SNAPSHOTS_API.md` - เอกสาร API ฉบับเต็ม
- `README.md` - คู่มือการติดตั้งและใช้งานระบบ

Happy Coding! 🚀
