import asyncio
import sqlite3
import os
import glob
import yaml
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from src.core.database.engine import AsyncSessionLocal, engine
from src.core.database.models import Base, APIKey, Quota, RateLimit, Config

# SQLite DB Path
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "superai.db")
# YAML Configs directory
YAML_CONFIGS_DIR = os.getenv("YAML_CONFIGS_DIR", ".")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("PostgreSQL schema initialized.")

async def migrate_sqlite_data():
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite database not found at {SQLITE_DB_PATH}. Skipping SQLite migration.")
        return

    print(f"Connecting to SQLite database at {SQLITE_DB_PATH}...")
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        async with AsyncSessionLocal() as session:
            # Migrate API Keys
            try:
                cursor.execute("SELECT key, user_id, is_active, created_at FROM api_keys")
                api_keys = cursor.fetchall()
                if api_keys:
                    print(f"Migrating {len(api_keys)} API keys...")
                    for row in api_keys:
                        created_at = row['created_at']
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.fromisoformat(created_at)
                            except ValueError:
                                created_at = datetime.utcnow()
                        
                        stmt = insert(APIKey).values(
                            key=row['key'],
                            user_id=row['user_id'],
                            is_active=bool(row['is_active']),
                            created_at=created_at
                        ).on_conflict_do_nothing(index_elements=['key'])
                        await session.execute(stmt)
            except sqlite3.OperationalError:
                print("Table 'api_keys' not found in SQLite or missing columns.")

            # Migrate Quotas
            try:
                cursor.execute("SELECT user_id, limit_value, used, reset_at FROM quotas")
                quotas = cursor.fetchall()
                if quotas:
                    print(f"Migrating {len(quotas)} quotas...")
                    for row in quotas:
                        reset_at = row['reset_at']
                        if isinstance(reset_at, str):
                            try:
                                reset_at = datetime.fromisoformat(reset_at)
                            except ValueError:
                                reset_at = datetime.utcnow()
                                
                        stmt = insert(Quota).values(
                            user_id=row['user_id'],
                            limit_value=row['limit_value'],
                            used=row['used'],
                            reset_at=reset_at
                        ).on_conflict_do_nothing(index_elements=['user_id'])
                        await session.execute(stmt)
            except sqlite3.OperationalError:
                print("Table 'quotas' not found in SQLite or missing columns.")

            # Migrate Rate Limits
            try:
                cursor.execute("SELECT user_id, requests_per_minute FROM rate_limits")
                rate_limits = cursor.fetchall()
                if rate_limits:
                    print(f"Migrating {len(rate_limits)} rate limits...")
                    for row in rate_limits:
                        stmt = insert(RateLimit).values(
                            user_id=row['user_id'],
                            requests_per_minute=row['requests_per_minute']
                        ).on_conflict_do_nothing(index_elements=['user_id'])
                        await session.execute(stmt)
            except sqlite3.OperationalError:
                print("Table 'rate_limits' not found in SQLite or missing columns.")

            # Migrate Configs
            try:
                cursor.execute("SELECT name, settings FROM configs")
                configs = cursor.fetchall()
                if configs:
                    print(f"Migrating {len(configs)} configs from SQLite...")
                    for row in configs:
                        settings = row['settings']
                        if isinstance(settings, str):
                            try:
                                settings = json.loads(settings)
                            except json.JSONDecodeError:
                                settings = {}
                        
                        stmt = insert(Config).values(
                            name=row['name'],
                            settings=settings
                        ).on_conflict_do_nothing(index_elements=['name'])
                        await session.execute(stmt)
            except sqlite3.OperationalError:
                print("Table 'configs' not found in SQLite or missing columns.")

            await session.commit()
            print("SQLite data migration completed successfully.")
    except Exception as e:
        print(f"Error during SQLite migration: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

async def migrate_yaml_configs():
    yaml_files = glob.glob(os.path.join(YAML_CONFIGS_DIR, "*.yaml")) + glob.glob(os.path.join(YAML_CONFIGS_DIR, "*.yml"))
    
    if not yaml_files:
        print(f"No YAML config files found in {YAML_CONFIGS_DIR}.")
        return

    print(f"Found {len(yaml_files)} YAML config files. Migrating...")
    async with AsyncSessionLocal() as session:
        for filepath in yaml_files:
            filename = os.path.basename(filepath)
            name = os.path.splitext(filename)[0]
            
            try:
                with open(filepath, 'r') as f:
                    settings = yaml.safe_load(f)
                    if not isinstance(settings, dict):
                        print(f"Warning: {filename} does not contain a YAML dictionary. Wrapping in dict.")
                        settings = {"data": settings}
                        
                stmt = insert(Config).values(
                    name=name,
                    settings=settings
                ).on_conflict_do_nothing(index_elements=['name'])
                await session.execute(stmt)
                print(f"Migrated config from {filename}.")
            except Exception as e:
                print(f"Error migrating {filename}: {e}")
                
        await session.commit()
        print("YAML configs migration completed successfully.")

async def main():
    print("Starting database migration...")
    await init_db()
    await migrate_sqlite_data()
    await migrate_yaml_configs()
    print("Migration finished safely.")

if __name__ == "__main__":
    asyncio.run(main())
