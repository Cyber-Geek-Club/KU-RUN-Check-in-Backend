"""
API Integration Test: Reward and Leaderboard Reward System
ทดสอบระบบรางวัลและ Leaderboard ผ่าน API Endpoints

Test Flow:
1. สร้าง Users ผ่าน API (Students + Staff/Organizer)
2. Login เพื่อรับ Token
3. สร้าง Events ผ่าน API
4. สร้าง Rewards ผ่าน API
5. สร้าง Leaderboard Config ผ่าน API
6. Users เข้าร่วมกิจกรรม (Join Events)
7. Staff Check-in Users
8. Verify/Complete participations
9. ตรวจสอบ Rewards & Leaderboard

Requirements:
    pip install httpx pytest pytest-asyncio

Usage:
    # รัน API Server ก่อน (ใน terminal อื่น):
    uvicorn main:app --reload --port 8000
    
    # รัน Test:
    python test_reward_api_integration.py
    
    # หรือใช้ pytest:
    pytest test_reward_api_integration.py -v
"""

import httpx
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import json

# ============================================
# Configuration
# ============================================

BASE_URL = "http://localhost:8000/api"

# Test Data Configuration
NUM_TEST_STUDENTS = 5
NUM_TEST_EVENTS = 3


# ============================================
# Test Data Classes
# ============================================

@dataclass
class TestUser:
    """เก็บข้อมูล User ที่สร้างระหว่างทดสอบ"""
    id: Optional[int] = None
    email: str = ""
    password: str = ""
    token: str = ""
    role: str = ""
    first_name: str = ""
    last_name: str = ""


@dataclass
class TestEvent:
    """เก็บข้อมูล Event ที่สร้างระหว่างทดสอบ"""
    id: Optional[int] = None
    title: str = ""


@dataclass
class TestReward:
    """เก็บข้อมูล Reward ที่สร้างระหว่างทดสอบ"""
    id: Optional[int] = None
    name: str = ""


@dataclass
class TestParticipation:
    """เก็บข้อมูล Participation ที่สร้างระหว่างทดสอบ"""
    id: Optional[int] = None
    join_code: str = ""
    user_id: Optional[int] = None
    event_id: Optional[int] = None
    status: str = ""


@dataclass
class TestContext:
    """เก็บ context ทั้งหมดของการทดสอบ"""
    organizer: Optional[TestUser] = None
    staff: Optional[TestUser] = None
    students: List[TestUser] = field(default_factory=list)
    events: List[TestEvent] = field(default_factory=list)
    rewards: List[TestReward] = field(default_factory=list)
    participations: Dict[int, List[TestParticipation]] = field(default_factory=dict)
    leaderboard_config_id: Optional[int] = None


# ============================================
# API Client Helper
# ============================================

class APIClient:
    """Helper class สำหรับเรียก API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    def _headers(self, token: str = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def post(self, endpoint: str, data: Dict, token: str = None) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        return await self.client.post(url, json=data, headers=self._headers(token))
    
    async def get(self, endpoint: str, token: str = None, params: Dict = None) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        return await self.client.get(url, headers=self._headers(token), params=params)
    
    async def put(self, endpoint: str, data: Dict, token: str = None) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        return await self.client.put(url, json=data, headers=self._headers(token))
    
    async def delete(self, endpoint: str, token: str = None) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        return await self.client.delete(url, headers=self._headers(token))


# ============================================
# Helper Functions
# ============================================

def generate_unique_suffix() -> str:
    """สร้าง suffix unique สำหรับ test data"""
    return f"{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"


def print_section(title: str):
    """พิมพ์หัวข้อ section"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_step(step: str, success: bool = True, detail: str = ""):
    """พิมพ์ผลลัพธ์ของแต่ละขั้นตอน"""
    icon = "✓" if success else "✗"
    color_start = "" if success else ""
    print(f"  {icon} {step}")
    if detail:
        print(f"      → {detail}")


def print_response_error(response: httpx.Response):
    """พิมพ์ error จาก response"""
    try:
        error = response.json()
        print(f"      Error: {error.get('detail', response.text)}")
    except:
        print(f"      Error: {response.text}")


# ============================================
# Test Steps
# ============================================

async def register_organizer(api: APIClient, ctx: TestContext) -> bool:
    """ลงทะเบียน Organizer"""
    suffix = generate_unique_suffix()
    
    data = {
        "email": f"organizer_{suffix}@ku.th",
        "password": "Organizer123!",
        "title": "นาย",
        "first_name": "ผู้จัดงาน",
        "last_name": f"ทดสอบ_{suffix}"
    }
    
    response = await api.post("/users/register/organizer", data)
    
    if response.status_code == 201:
        result = response.json()
        ctx.organizer = TestUser(
            id=result["id"],
            email=data["email"],
            password=data["password"],
            role="organizer",
            first_name=data["first_name"],
            last_name=data["last_name"]
        )
        print_step(f"Registered Organizer: {ctx.organizer.email} (ID: {ctx.organizer.id})")
        return True
    else:
        print_step("Register Organizer", False)
        print_response_error(response)
        return False


async def register_staff(api: APIClient, ctx: TestContext) -> bool:
    """ลงทะเบียน Staff"""
    suffix = generate_unique_suffix()
    
    data = {
        "email": f"staff_{suffix}@ku.th",
        "password": "Staff123!",
        "title": "นาย",
        "first_name": "เจ้าหน้าที่",
        "last_name": f"ทดสอบ_{suffix}",
        "department": "กองกิจกรรมนักศึกษา"
    }
    
    response = await api.post("/users/register/staff", data)
    
    if response.status_code == 201:
        result = response.json()
        ctx.staff = TestUser(
            id=result["id"],
            email=data["email"],
            password=data["password"],
            role="staff",
            first_name=data["first_name"],
            last_name=data["last_name"]
        )
        print_step(f"Registered Staff: {ctx.staff.email} (ID: {ctx.staff.id})")
        return True
    else:
        print_step("Register Staff", False)
        print_response_error(response)
        return False


async def register_students(api: APIClient, ctx: TestContext, count: int) -> bool:
    """ลงทะเบียน Students หลายคน"""
    success_count = 0
    
    for i in range(1, count + 1):
        suffix = generate_unique_suffix()
        
        data = {
            "email": f"student{i}_{suffix}@ku.th",
            "password": "Student123!",
            "title": "นาย" if i % 2 == 0 else "นางสาว",
            "first_name": f"นักศึกษา{i}",
            "last_name": f"ทดสอบ_{suffix}",
            "nisit_id": f"65{i:08d}",
            "major": "วิทยาการคอมพิวเตอร์",
            "faculty": "วิศวกรรมศาสตร์"
        }
        
        response = await api.post("/users/register/student", data)
        
        if response.status_code == 201:
            result = response.json()
            student = TestUser(
                id=result["id"],
                email=data["email"],
                password=data["password"],
                role="student",
                first_name=data["first_name"],
                last_name=data["last_name"]
            )
            ctx.students.append(student)
            success_count += 1
            print_step(f"Registered Student: {student.email} (ID: {student.id})")
        else:
            print_step(f"Register Student {i}", False)
            print_response_error(response)
    
    return success_count == count


async def login_user(api: APIClient, user: TestUser) -> bool:
    """Login และเก็บ token"""
    data = {
        "email": user.email,
        "password": user.password
    }
    
    response = await api.post("/users/login", data)
    
    if response.status_code == 200:
        result = response.json()
        user.token = result.get("access_token", "")
        if user.token:
            print_step(f"Logged in: {user.email}")
            return True
    
    print_step(f"Login {user.email}", False)
    print_response_error(response)
    return False


async def login_all_users(api: APIClient, ctx: TestContext) -> bool:
    """Login ทุกคนและเก็บ token"""
    # Verify users first (ข้าม verification เพราะเราต้องเข้าถึง database โดยตรง)
    # ในการทดสอบจริง อาจต้อง call verify endpoint หรือตั้งค่า is_verified ใน database
    
    all_success = True
    
    # Login organizer
    if ctx.organizer:
        if not await login_user(api, ctx.organizer):
            all_success = False
    
    # Login staff
    if ctx.staff:
        if not await login_user(api, ctx.staff):
            all_success = False
    
    # Login students
    for student in ctx.students:
        if not await login_user(api, student):
            all_success = False
    
    return all_success


async def create_events(api: APIClient, ctx: TestContext, count: int) -> bool:
    """สร้าง Events"""
    if not ctx.organizer or not ctx.organizer.token:
        print_step("Create Events - No organizer token", False)
        return False
    
    base_date = datetime.now(timezone.utc) + timedelta(days=1)
    success_count = 0
    
    for i in range(1, count + 1):
        data = {
            "title": f"KU Run Test Event #{i}",
            "description": f"กิจกรรมวิ่งทดสอบครั้งที่ {i}",
            "event_type": "single_day",
            "event_date": (base_date + timedelta(days=i)).isoformat(),
            "location": "สนามกีฬา มหาวิทยาลัยเกษตรศาสตร์",
            "distance_km": 5,
            "max_participants": 100,
            "is_active": True,
            "is_published": True
        }
        
        response = await api.post("/events/", data, ctx.organizer.token)
        
        if response.status_code == 201:
            result = response.json()
            event = TestEvent(id=result["id"], title=result["title"])
            ctx.events.append(event)
            success_count += 1
            print_step(f"Created Event: {event.title} (ID: {event.id})")
        else:
            print_step(f"Create Event {i}", False)
            print_response_error(response)
    
    return success_count == count


async def create_rewards(api: APIClient, ctx: TestContext) -> bool:
    """สร้าง Rewards"""
    if not ctx.organizer or not ctx.organizer.token:
        print_step("Create Rewards - No organizer token", False)
        return False
    
    rewards_data = [
        {
            "name": "🥉 Bronze Runner",
            "description": "เหรียญทองแดงสำหรับผู้ที่วิ่งครบ 3 ครั้ง",
            "badge_image_url": "https://example.com/bronze.png",
            "required_completions": 3,
            "time_period_days": 30
        },
        {
            "name": "🥈 Silver Runner",
            "description": "เหรียญเงินสำหรับผู้ที่วิ่งครบ 5 ครั้ง",
            "badge_image_url": "https://example.com/silver.png",
            "required_completions": 5,
            "time_period_days": 30
        },
        {
            "name": "🥇 Gold Runner",
            "description": "เหรียญทองสำหรับผู้ที่วิ่งครบ 10 ครั้ง",
            "badge_image_url": "https://example.com/gold.png",
            "required_completions": 10,
            "time_period_days": 30
        }
    ]
    
    success_count = 0
    
    for reward_data in rewards_data:
        response = await api.post("/rewards/", reward_data, ctx.organizer.token)
        
        if response.status_code == 201:
            result = response.json()
            reward = TestReward(id=result["id"], name=result["name"])
            ctx.rewards.append(reward)
            success_count += 1
            print_step(f"Created Reward: {reward.name} (ID: {reward.id})")
        else:
            print_step(f"Create Reward: {reward_data['name']}", False)
            print_response_error(response)
    
    return success_count == len(rewards_data)


async def create_leaderboard_config(api: APIClient, ctx: TestContext) -> bool:
    """สร้าง Leaderboard Config"""
    if not ctx.organizer or not ctx.organizer.token:
        print_step("Create Leaderboard - No organizer token", False)
        return False
    
    if not ctx.events:
        print_step("Create Leaderboard - No events", False)
        return False
    
    if len(ctx.rewards) < 3:
        print_step("Create Leaderboard - Not enough rewards", False)
        return False
    
    now = datetime.now(timezone.utc)
    
    data = {
        "event_id": ctx.events[0].id,
        "name": "KU Run 2026 Leaderboard Test",
        "description": "Leaderboard ทดสอบสำหรับ Integration Test",
        "required_completions": 1,  # ตั้งต่ำเพื่อให้ทดสอบได้ง่าย
        "max_reward_recipients": 50,
        "reward_tiers": [
            {
                "tier": 1,
                "min_rank": 1,
                "max_rank": 2,
                "reward_id": ctx.rewards[2].id,  # Gold
                "reward_name": ctx.rewards[2].name,
                "quantity": 2,
                "required_completions": 3
            },
            {
                "tier": 2,
                "min_rank": 3,
                "max_rank": 5,
                "reward_id": ctx.rewards[1].id,  # Silver
                "reward_name": ctx.rewards[1].name,
                "quantity": 3,
                "required_completions": 2
            },
            {
                "tier": 3,
                "min_rank": 6,
                "max_rank": 50,
                "reward_id": ctx.rewards[0].id,  # Bronze
                "reward_name": ctx.rewards[0].name,
                "quantity": 45,
                "required_completions": 1
            }
        ],
        "starts_at": (now - timedelta(days=1)).isoformat(),
        "ends_at": (now + timedelta(days=30)).isoformat()
    }
    
    response = await api.post("/reward-leaderboards/configs", data, ctx.organizer.token)
    
    if response.status_code == 201:
        result = response.json()
        ctx.leaderboard_config_id = result["id"]
        print_step(f"Created Leaderboard Config: {result['name']} (ID: {result['id']})")
        return True
    else:
        print_step("Create Leaderboard Config", False)
        print_response_error(response)
        return False


async def students_join_events(api: APIClient, ctx: TestContext) -> bool:
    """นักศึกษาเข้าร่วมกิจกรรม"""
    if not ctx.events:
        print_step("Join Events - No events", False)
        return False
    
    success = True
    
    for i, student in enumerate(ctx.students):
        if not student.token:
            print_step(f"Join Events - No token for student {student.id}", False)
            success = False
            continue
        
        ctx.participations[student.id] = []
        
        # แต่ละคนเข้าร่วมจำนวนกิจกรรมต่างกัน (1, 2, 3, ... events)
        events_to_join = ctx.events[:min(len(ctx.events), i + 1)]
        
        for event in events_to_join:
            data = {"event_id": event.id}
            response = await api.post("/participations/join", data, student.token)
            
            if response.status_code == 201:
                result = response.json()
                participation = TestParticipation(
                    id=result["id"],
                    join_code=result["join_code"],
                    user_id=student.id,
                    event_id=event.id,
                    status=result["status"]
                )
                ctx.participations[student.id].append(participation)
                print_step(f"Student {student.id} joined Event {event.id} (Code: {participation.join_code})")
            else:
                print_step(f"Student {student.id} join Event {event.id}", False)
                print_response_error(response)
                success = False
    
    return success


async def staff_checkin_students(api: APIClient, ctx: TestContext) -> bool:
    """Staff check-in นักศึกษา"""
    if not ctx.staff or not ctx.staff.token:
        print_step("Check-in - No staff token", False)
        return False
    
    success = True
    
    for user_id, participations in ctx.participations.items():
        for participation in participations:
            data = {"join_code": participation.join_code}
            response = await api.post("/participations/check-in", data, ctx.staff.token)
            
            if response.status_code == 200:
                result = response.json()
                participation.status = result["status"]
                print_step(f"Checked-in: {participation.join_code} -> {participation.status}")
            else:
                print_step(f"Check-in {participation.join_code}", False)
                print_response_error(response)
                success = False
    
    return success


async def verify_completions(api: APIClient, ctx: TestContext) -> bool:
    """Staff verify/complete การเข้าร่วม"""
    if not ctx.staff or not ctx.staff.token:
        print_step("Verify - No staff token", False)
        return False
    
    success = True
    
    for user_id, participations in ctx.participations.items():
        for participation in participations:
            # ข้ามถ้ายังไม่ได้ check-in
            if participation.status != "checked_in":
                continue
            
            data = {
                "participation_id": participation.id,
                "approved": True,
                "rejection_reason": None
            }
            response = await api.post("/participations/verify", data, ctx.staff.token)
            
            if response.status_code == 200:
                result = response.json()
                participation.status = result["status"]
                print_step(f"Verified: Participation {participation.id} -> {participation.status}")
            else:
                print_step(f"Verify Participation {participation.id}", False)
                print_response_error(response)
                success = False
    
    return success


async def calculate_leaderboard_rewards(api: APIClient, ctx: TestContext) -> bool:
    """คำนวณและจัดสรรรางวัล Leaderboard"""
    if not ctx.organizer or not ctx.organizer.token:
        print_step("Calculate Leaderboard - No organizer token", False)
        return False
    
    if not ctx.leaderboard_config_id:
        print_step("Calculate Leaderboard - No config", False)
        return False
    
    # Calculate ranks
    response = await api.post(
        f"/reward-leaderboards/configs/{ctx.leaderboard_config_id}/calculate-ranks",
        {},
        ctx.organizer.token
    )
    
    if response.status_code == 200:
        result = response.json()
        print_step(f"Calculated Leaderboard Rewards")
        print(f"      Stats: {json.dumps(result, indent=2, default=str)}")
        return True
    else:
        print_step("Calculate Leaderboard Rewards", False)
        print_response_error(response)
        return False


async def check_user_rewards(api: APIClient, ctx: TestContext) -> bool:
    """ตรวจสอบรางวัลของนักศึกษา"""
    success = True
    
    for student in ctx.students:
        if not student.token:
            continue
        
        response = await api.get(f"/rewards/user/{student.id}", student.token)
        
        if response.status_code == 200:
            result = response.json()
            reward_count = len(result)
            print_step(f"User {student.id} has {reward_count} reward(s)")
            for r in result:
                print(f"      → Reward ID: {r['reward_id']}, Earned: {r['earned_at']}")
        else:
            print_step(f"Check rewards for User {student.id}", False)
            print_response_error(response)
            success = False
    
    return success


async def display_leaderboard(api: APIClient, ctx: TestContext) -> bool:
    """แสดง Leaderboard"""
    if not ctx.organizer or not ctx.organizer.token:
        print_step("Display Leaderboard - No organizer token", False)
        return False
    
    if not ctx.leaderboard_config_id:
        print_step("Display Leaderboard - No config", False)
        return False
    
    response = await api.get(
        f"/reward-leaderboards/configs/{ctx.leaderboard_config_id}/entries",
        ctx.organizer.token
    )
    
    if response.status_code == 200:
        entries = response.json()
        
        print("\n" + "-" * 60)
        print("📊 LEADERBOARD")
        print("-" * 60)
        
        if not entries:
            print("  (No entries)")
        else:
            print(f"  {'Rank':<6}{'User ID':<10}{'Completions':<15}{'Tier':<15}{'Reward':<12}")
            print("  " + "-" * 55)
            
            for entry in entries:
                rank = entry.get("rank") or "-"
                tier = entry.get("reward_tier") or "N/A"
                reward_id = entry.get("reward_id") or "-"
                completions = entry.get("total_completions", 0)
                
                print(f"  {rank:<6}{entry['user_id']:<10}{completions:<15}{tier:<15}{reward_id:<12}")
        
        return True
    else:
        print_step("Display Leaderboard", False)
        print_response_error(response)
        return False


# ============================================
# Main Test Runner
# ============================================

async def run_api_integration_test():
    """รัน Integration Test ทั้งหมด"""
    print("\n" + "=" * 70)
    print("  🚀 REWARD & LEADERBOARD API INTEGRATION TEST")
    print("=" * 70)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API Base URL: {BASE_URL}")
    
    # Initialize
    api = APIClient(BASE_URL)
    ctx = TestContext()
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "steps": []
    }
    
    try:
        # Step 1: Register Users
        print_section("STEP 1: Register Users")
        
        if await register_organizer(api, ctx):
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
        
        if await register_staff(api, ctx):
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
        
        if await register_students(api, ctx, NUM_TEST_STUDENTS):
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
        
        # Step 2: Login Users
        print_section("STEP 2: Login Users")
        
        # หมายเหตุ: ในการทดสอบจริง ต้อง verify email ก่อน
        # สำหรับทดสอบ เราอาจต้องตั้งค่า is_verified = True ใน database โดยตรง
        # หรือปิด email verification ชั่วคราว
        
        print("  ⚠️  Note: Users need to be verified before login")
        print("      Run this SQL to verify test users:")
        print("      UPDATE users SET is_verified = true WHERE email LIKE '%_test_%';")
        
        if await login_all_users(api, ctx):
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            print("  ⚠️  Login failed - Users may need email verification")
            print("      Continuing with limited functionality...")
        
        # Step 3: Create Events (requires organizer token)
        print_section("STEP 3: Create Events")
        
        if ctx.organizer and ctx.organizer.token:
            if await create_events(api, ctx, NUM_TEST_EVENTS):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No organizer token")
            test_results["failed"] += 1
        
        # Step 4: Create Rewards
        print_section("STEP 4: Create Rewards")
        
        if ctx.organizer and ctx.organizer.token:
            if await create_rewards(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No organizer token")
            test_results["failed"] += 1
        
        # Step 5: Create Leaderboard Config
        print_section("STEP 5: Create Leaderboard Config")
        
        if ctx.organizer and ctx.organizer.token and ctx.events and ctx.rewards:
            if await create_leaderboard_config(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - Missing prerequisites")
            test_results["failed"] += 1
        
        # Step 6: Students Join Events
        print_section("STEP 6: Students Join Events")
        
        if any(s.token for s in ctx.students) and ctx.events:
            if await students_join_events(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No student tokens or events")
            test_results["failed"] += 1
        
        # Step 7: Staff Check-in
        print_section("STEP 7: Staff Check-in Students")
        
        if ctx.staff and ctx.staff.token and ctx.participations:
            if await staff_checkin_students(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No staff token or participations")
            test_results["failed"] += 1
        
        # Step 8: Verify/Complete
        print_section("STEP 8: Verify Completions")
        
        if ctx.staff and ctx.staff.token:
            if await verify_completions(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No staff token")
            test_results["failed"] += 1
        
        # Step 9: Calculate Leaderboard Rewards
        print_section("STEP 9: Calculate Leaderboard Rewards")
        
        if ctx.leaderboard_config_id:
            if await calculate_leaderboard_rewards(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No leaderboard config")
            test_results["failed"] += 1
        
        # Step 10: Check User Rewards
        print_section("STEP 10: Check User Rewards")
        
        if any(s.token for s in ctx.students):
            if await check_user_rewards(api, ctx):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
        else:
            print("  ⚠️  Skipped - No student tokens")
            test_results["failed"] += 1
        
        # Display Leaderboard
        print_section("LEADERBOARD RESULTS")
        await display_leaderboard(api, ctx)
        
        # Summary
        print("\n" + "=" * 70)
        print("  📊 TEST SUMMARY")
        print("=" * 70)
        print(f"  ✓ Passed: {test_results['passed']}")
        print(f"  ✗ Failed: {test_results['failed']}")
        print(f"  Total Steps: {test_results['passed'] + test_results['failed']}")
        
        if test_results['failed'] == 0:
            print("\n  🎉 ALL TESTS PASSED!")
        else:
            print(f"\n  ⚠️  {test_results['failed']} test(s) failed")
        
        print("\n" + "=" * 70)
        print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
    
    except Exception as e:
        print(f"\n  ❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()


# ============================================
# Entry Point
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  📋 PRE-TEST CHECKLIST")
    print("=" * 70)
    print("""
  Before running this test, ensure:
  
  1. ✅ API Server is running:
     uvicorn main:app --reload --port 8000
     
  2. ✅ Database is configured and accessible
  
  3. ✅ (Optional) Disable email verification for testing:
     Or run SQL after registration:
     UPDATE users SET is_verified = true WHERE email LIKE '%test%';
     
  4. ✅ Required packages installed:
     pip install httpx
    """)
    print("=" * 70)
    
    input("  Press Enter to start the test...")
    
    asyncio.run(run_api_integration_test())
