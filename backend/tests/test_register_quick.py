"""Isolate the 500: test each step of registration independently."""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

async def test():
    print("1. Testing password hashing...")
    try:
        from app.auth.deps import hash_password, verify_password
        h = hash_password("test123456")
        assert verify_password("test123456", h)
        print("   OK: password hashing works")
    except Exception as e:
        print(f"   FAIL: {e}")
        return

    print("2. Testing database connection...")
    try:
        from app.database import AsyncSessionLocal, init_db, engine
        async with engine.begin() as conn:
            from app.database import Base
            await conn.run_sync(Base.metadata.create_all)
        print("   OK: tables created")
    except Exception as e:
        print(f"   FAIL: {e}")
        return

    print("3. Testing User model insert...")
    try:
        from app.models.user import User
        from app.auth.deps import hash_password
        import secrets
        from datetime import datetime, timedelta

        async with AsyncSessionLocal() as db:
            user = User(
                email="diag_test@test.com",
                hashed_password=hash_password("test123456"),
                full_name="Diag Test",
                created_at=datetime.utcnow(),
            )
            user.email_verification_token = secrets.token_urlsafe(32)
            user.email_token_expires = datetime.utcnow() + timedelta(hours=24)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"   OK: user created with id={user.id}")

            # Cleanup
            await db.delete(user)
            await db.commit()
            print("   OK: user deleted")
    except Exception as e:
        print(f"   FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
