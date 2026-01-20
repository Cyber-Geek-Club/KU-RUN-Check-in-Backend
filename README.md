## Tests
All test scripts are in the `tests/` directory.

```
Quick run (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Ensure TEST_DATABASE_URL points to a test database (must include "test")
setx TEST_DATABASE_URL "postgresql+asyncpg://user:pass@localhost/test_db"
pytest tests/ -v
```

## Documentation
Project documentation files are in the `docs/` directory.

## Scripts
Utility scripts (safe test DB helpers) are in the `scripts/` directory — for example `scripts/clear_test_db.py`.
