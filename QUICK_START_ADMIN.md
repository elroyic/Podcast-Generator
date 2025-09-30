# Quick Start: Admin Panel

## 🚀 Get Started in 3 Steps

### Step 1: Create Your Admin User
```bash
python init_admin_user.py
```

Follow the prompts to create your admin account.

### Step 2: Start the Services
```bash
# If using Docker
docker-compose up -d

# Or if running locally
python -m uvicorn services.api-gateway.main:app --host 0.0.0.0 --port 8000
```

### Step 3: Access the Admin Panel
1. Open browser: `http://localhost:8000/login`
2. Login with your admin credentials
3. Click "Admin" in the navigation bar

## 📋 Quick Actions

### Add a New User
1. **Admin Panel** → **User Management** tab
2. Click **"Add User"** button
3. Fill in:
   - Username (unique, cannot be changed)
   - Email
   - Password (min 8 characters)
   - Role (Admin/Editor/User)
4. Click **"Add User"**

### Change Your Password
1. **Admin Panel** → **Change Admin Password** tab
2. Enter:
   - Current password
   - New password
   - Confirm new password
3. Click **"Update Password"**

### Edit a User
1. Find user in the table
2. Click **"Edit"**
3. Modify email, role, or active status
4. Click **"Update User"**

### Delete a User
1. Find user in the table
2. Click **"Delete"**
3. Confirm deletion

**Note**: You cannot delete your own account.

## 🔐 User Roles

| Role | Can Manage Users | Can Edit Content | Can View Content |
|------|-----------------|------------------|------------------|
| **Admin** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Editor** | ❌ No | ✅ Yes | ✅ Yes |
| **User** | ❌ No | ❌ No | ✅ Yes |

## 🔑 Default Credentials (Environment Variables)

If you haven't created database users yet, you can use:
- Username: `admin` (or `ADMIN_USERNAME` env var)
- Password: `admin123` (or `ADMIN_PASSWORD` env var)

**⚠️ Important**: Change this in production!

## 📖 Need More Help?

See the full documentation:
- **Detailed Guide**: `Docs/Current/Admin-Panel-Guide.md`
- **Complete Summary**: `ADMIN_PANEL_SUMMARY.md`

## 🐛 Common Issues

**Problem**: Can't login
- **Solution**: Run `python init_admin_user.py` to create admin user

**Problem**: "Authentication required" error
- **Solution**: Make sure you're logged in; token expires after 24 hours

**Problem**: Can't see Admin link
- **Solution**: Ensure you have "admin" role assigned

## 💡 Tips

1. **Strong Passwords**: Use at least 8 characters, mix letters/numbers/symbols
2. **Individual Accounts**: Create separate accounts for each admin
3. **Regular Audits**: Review user list periodically
4. **Backup**: Ensure database is backed up regularly

---

**Ready to go?** Run `python init_admin_user.py` now! 🎉
