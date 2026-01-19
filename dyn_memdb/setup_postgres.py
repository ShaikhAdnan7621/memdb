"""
PostgreSQL setup helper for MemDB testing
"""

import asyncio
import asyncpg
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_test_database():
    """Setup test database and verify connection"""
    
    # Common PostgreSQL configurations to try
    configs = [
        "postgresql://postgres:password@localhost:5432/postgres",
        "postgresql://postgres:postgres@localhost:5432/postgres", 
        "postgresql://user:password@localhost:5432/postgres",
        "postgresql://postgres@localhost:5432/postgres",
    ]
    
    print("Trying to connect to PostgreSQL...")
    
    for db_url in configs:
        try:
            print(f"Trying: {db_url}")
            conn = await asyncpg.connect(db_url)
            
            # Test connection
            result = await conn.fetchval("SELECT version()")
            print(f"✓ Connected! PostgreSQL version: {result[:50]}...")
            
            # Create test database
            try:
                await conn.execute("CREATE DATABASE memdb_test")
                print("✓ Created test database: memdb_test")
            except asyncpg.DuplicateDatabaseError:
                print("✓ Test database already exists: memdb_test")
            
            await conn.close()
            
            # Update .env file
            test_db_url = db_url.replace("/postgres", "/memdb_test")
            with open(".env", "w") as f:
                f.write(f"DATABASE_URL={test_db_url}\n")
            
            print(f"✓ Updated .env with: {test_db_url}")
            print("\nYou can now run: python test_memdb.py")
            return test_db_url
            
        except Exception as e:
            print(f"✗ Failed: {e}")
            continue
    
    print("\n❌ Could not connect to PostgreSQL!")
    print("\nTo fix this:")
    print("1. Install PostgreSQL: https://www.postgresql.org/download/")
    print("2. Start PostgreSQL service")
    print("3. Create a user/password or use default postgres user")
    print("4. Update the DATABASE_URL in .env file")
    print("\nAlternatively, run the standalone test:")
    print("python test_standalone.py")
    
    return None

if __name__ == "__main__":
    asyncio.run(setup_test_database())