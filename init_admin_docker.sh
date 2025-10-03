#!/bin/bash
# Initialize admin user using Docker exec

echo "=================================================="
echo "Podcast AI - Admin User Initialization (Docker)"
echo "=================================================="
echo ""

# Run Python script inside the api-gateway container
docker compose exec api-gateway python - <<EOF
import os
import sys
from getpass import getpass

# Add shared to path
sys.path.insert(0, '/app')

from passlib.context import CryptContext
from shared.database import SessionLocal, create_tables
from shared.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

print("Creating database tables...")
create_tables()
print("✅ Database tables created/verified.")
print()

# Create database session
db = SessionLocal()

try:
    # Check if any admin users exist
    admin_count = db.query(User).filter(User.role == "admin").count()
    
    if admin_count > 0:
        print(f"ℹ️  {admin_count} admin user(s) already exist in the database.")
        response = input("Do you want to create another admin user? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    # Get admin details
    print()
    username = input("Enter admin username (default: admin): ").strip()
    if not username:
        username = "admin"
    
    # Check if username exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"❌ User '{username}' already exists.")
        sys.exit(1)
    
    email = input(f"Enter admin email (default: admin@podcast.ai): ").strip()
    if not email:
        email = "admin@podcast.ai"
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        print(f"❌ Email '{email}' is already registered.")
        sys.exit(1)
    
    password = input("Enter password (min 8 chars): ").strip()
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long.")
        sys.exit(1)
    
    # Create admin user
    admin_user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role="admin",
        is_active=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    print()
    print("=" * 60)
    print(f"✅ Admin user '{username}' created successfully!")
    print(f"   Email: {email}")
    print(f"   Role: {admin_user.role}")
    print(f"   ID: {admin_user.id}")
    print()
    print("You can now log in to the admin panel at:")
    print("  http://localhost:8000/admin-panel")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
EOF

echo ""
echo "Done!"

