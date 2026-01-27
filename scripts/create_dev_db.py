import asyncio
import asyncpg
import os
from urllib.parse import urlparse

# URL from .env (Master DB)
# DATABASE_URL=postgresql+asyncpg://postgres:B237812341b+@localhost:5432/ku_run
DB_URL = "postgresql://postgres:B237812341b+@127.0.0.1:5432/ku_run" # Changed localhost to 127.0.0.1
NEW_DB_NAME = "ku_run_dev"

async def create_database():
    parsed = urlparse(DB_URL)
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port
    
    print(f"Connecting to PostgreSQL at {host}:{port} as {user}...")
    
    try:
        # Connect to 'postgres' system db
        sys_conn = await asyncpg.connect(
            user=user, 
            password=password, 
            host=host, 
            port=port, 
            database='postgres'
        )
        
        # Check if exists
        exists = await sys_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", NEW_DB_NAME
        )
        
        if not exists:
            print(f"Creating database '{NEW_DB_NAME}'...")
            await sys_conn.execute(f'CREATE DATABASE "{NEW_DB_NAME}"')
            print(f"Database '{NEW_DB_NAME}' created successfully!")
        else:
            print(f"Database '{NEW_DB_NAME}' already exists.")
            
        await sys_conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    asyncio.run(create_database())
