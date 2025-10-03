#!/usr/bin/env python3
"""
Initialize admin user in the database.
Run this script once to create the initial admin user.
"""
import os
import sys
from getpass import getpass

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from shared.database import SessionLocal, create_tables
from shared.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_admin_user(
    db: Session,
    username: str = "admin",
    email: str = "admin@podcast.ai",
    password: str = None
):
    """Create an admin user if it doesn't exist."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"❌ User '{username}' already exists.")
        return False
    
    # If password not provided, prompt for it
    if not password:
        password = getpass(f"Enter password for admin user '{username}': ")
        confirm_password = getpass("Confirm password: ")
        
        if password != confirm_password:
            print("❌ Passwords do not match.")
            return False
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long.")
            return False
    
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
    
    print(f"✅ Admin user '{username}' created successfully!")
    print(f"   Email: {email}")
    print(f"   Role: {admin_user.role}")
    print(f"   ID: {admin_user.id}")
    
    return True


def main():
    """Main function."""
    print("=" * 60)
    print("Podcast AI - Admin User Initialization")
    print("=" * 60)
    print()
    
    # Create tables if they don't exist
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
                return
        
        # Get admin details
        print()
        username = input("Enter admin username (default: admin): ").strip()
        if not username:
            username = "admin"
        
        email = input(f"Enter admin email (default: admin@podcast.ai): ").strip()
        if not email:
            email = "admin@podcast.ai"
        
        # Create the admin user
        print()
        success = create_admin_user(db, username, email)
        
        if success:
            print()
            print("=" * 60)
            print("Admin user created successfully!")
            print("You can now log in to the admin panel at: http://localhost:8000/admin-panel")
            print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
