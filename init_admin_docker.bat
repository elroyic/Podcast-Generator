@echo off
REM Initialize admin user using Docker exec (Windows batch file)

echo ==================================================
echo Podcast AI - Admin User Initialization (Docker)
echo ==================================================
echo.

REM Run Python script inside the api-gateway container
docker compose exec -T api-gateway python -c "import os; import sys; sys.path.insert(0, '/app'); from passlib.context import CryptContext; from shared.database import SessionLocal, create_tables; from shared.models import User; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print('Creating database tables...'); create_tables(); print('Database tables created/verified.'); print(); db = SessionLocal(); admin_count = db.query(User).filter(User.role == 'admin').count(); print(f'{admin_count} admin user(s) exist.'); username = 'admin'; email = 'admin@podcast.ai'; password = 'admin123'; existing = db.query(User).filter(User.username == username).first(); [db.close(), sys.exit(0) if existing else None]; user = User(username=username, email=email, hashed_password=pwd_context.hash(password), role='admin', is_active=True); db.add(user); db.commit(); db.refresh(user); print(f'\nAdmin user created: {username}'); print(f'Password: {password}'); print(f'Login at: http://localhost:8000/admin-panel'); db.close()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo Default admin credentials created:
    echo Username: admin
    echo Password: admin123
    echo.
    echo Login at: http://localhost:8000/admin-panel
    echo ====================================
) else (
    echo.
    echo Error occurred or admin user already exists.
    echo Try logging in with existing credentials.
)

echo.
pause

