import asyncio
import sys
from pathlib import Path
import bcrypt
import getpass

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from db.session import AsyncSessionLocal

# Import ALL models to ensure proper mapper configuration
from models.user import User, RoleEnum
from models.team import Team
from models.project import Project 
from models.task import Task
from models.revenue import Revenue
from models.meeting import Meeting


async def create_admin():
    """Create initial admin user with interactive input"""
    print("=" * 50)
    print("CREATE ADMIN USER")
    print("=" * 50)
    
    # Get user input
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")
    
    # Validate input
    if not username or not email or not password:
        print("❌ Error: All fields are required!")
        return
    
    if password != password_confirm:
        print("❌ Error: Passwords don't match!")
        return
    
    if len(password) < 8:
        print("❌ Error: Password must be at least 8 characters!")
        return
    
    async with AsyncSessionLocal() as db:
        # Check if user already exists
        result = await db.execute(
            select(User).filter(
                (User.username == username) | (User.email == email)
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"❌ Error: User with this username or email already exists!")
            return
        
        # Hash password with bcrypt
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create admin user
        admin = User(
            username=username,
            email=email,
            hashed_password=hashed.decode('utf-8'),
            role=RoleEnum.ADMIN,
            is_active=True
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        print()
        print("=" * 50)
        print("✅ Admin user created successfully!")
        print("=" * 50)
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role.value}")
        print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")