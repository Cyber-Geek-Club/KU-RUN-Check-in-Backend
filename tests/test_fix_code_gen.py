import sys
import os
import string
import asyncio

# Use relative path setup for test execution if needed, or just imports
# Assuming running from root
sys.path.append(os.getcwd())

from src.crud.event_participation_crud import generate_join_code

async def test_code_generation():
    print("Testing generate_join_code()...")
    
    # 1. Check format
    code = generate_join_code()
    print(f"Sample Code: {code}")
    
    assert len(code) == 5, "Code length must be 5"
    assert all(c in (string.ascii_uppercase + string.digits) for c in code), "Code must be alphanumeric"
    
    # 2. Check variety/entropy (basic)
    codes = {generate_join_code() for _ in range(1000)}
    print(f"Generated 1000 codes, unique count: {len(codes)}")
    assert len(codes) == 1000, "Should generate unique codes easily in empty space"
    
    # 3. Check for letters (to ensure it's not still just numbers)
    has_letters = any(c in string.ascii_uppercase for code in codes for c in code)
    print(f"Contains letters: {has_letters}")
    assert has_letters, "Should contain letters now"

    print("[OK] Test Passed: Code format is correct.")

if __name__ == "__main__":
    asyncio.run(test_code_generation())
