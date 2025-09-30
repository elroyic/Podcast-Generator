# Admin Panel Guide

## Overview

The Admin Panel provides centralized user management and admin password administration for the Podcast AI system.

## Features

### 1. User Management
- Create new users with different roles (Admin, Editor, User)
- Edit user information (email, role, active status)
- Delete users (with protection against self-deletion)
- View user login history

### 2. Password Management
- Change admin password securely
- Password requirements: minimum 8 characters
- Current password verification required

## Access

The Admin Panel is available at:
- **URL**: `http://localhost:8000/admin-panel`
- **Authentication**: Requires admin role login

## Getting Started

### Initial Setup

1. **Create the first admin user** using the initialization script:
   ```bash
   python init_admin_user.py
   ```

2. **Log in** to the system at `http://localhost:8000/login`

3. **Navigate to Admin Panel** using the "Admin" link in the navigation bar

### Using Docker

If using Docker Compose, the database tables will be created automatically on startup.

## User Roles

### Admin
- Full system access
- Can manage all users
- Can create/edit/delete podcast groups and episodes
- Can access all admin panels

### Editor
- Can create and edit content
- Cannot manage users
- Limited admin access

### User
- Read-only access
- Can view but not modify content

## Authentication

### Database Users (Primary)
Users created through the Admin Panel are stored in the database with:
- Hashed passwords (bcrypt)
- Role-based access control
- Login tracking

### Environment Variables (Fallback)
For backward compatibility, the system still supports login via environment variables:
- `ADMIN_USERNAME`: Default admin username (default: "admin")
- `ADMIN_PASSWORD`: Default admin password (default: "admin123")

**Note**: Database users take precedence over environment variable authentication.

## User Management

### Adding a User

1. Click "Add User" button
2. Fill in the form:
   - **Username**: Unique identifier (cannot be changed later)
   - **Email**: User's email address
   - **Password**: Minimum 8 characters
   - **Role**: Select from Admin, Editor, or User

3. Click "Add User" to create

### Editing a User

1. Click "Edit" next to the user
2. Modify:
   - Email address
   - Role
   - Active status (enable/disable account)

3. Click "Update User" to save changes

**Note**: Username cannot be changed after creation.

### Deleting a User

1. Click "Delete" next to the user
2. Confirm the deletion
3. User will be permanently removed from the database

**Protection**: You cannot delete your own account while logged in.

## Password Management

### Changing Your Password

1. Navigate to "Change Admin Password" tab
2. Enter:
   - **Current Password**: Your existing password
   - **New Password**: Must be at least 8 characters
   - **Confirm New Password**: Must match new password

3. Click "Update Password"

### Password Security

- Passwords are hashed using bcrypt
- Minimum length: 8 characters
- Current password verification required
- No password recovery (contact system administrator)

## API Endpoints

### User Management (Admin Only)

- `GET /api/users` - List all users
- `POST /api/users` - Create a new user
- `GET /api/users/{user_id}` - Get user details
- `PUT /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user

### Password Management (Authenticated)

- `PUT /api/users/me/password` - Change own password

## Security Considerations

1. **Password Strength**: Enforce minimum 8 characters (consider stronger requirements in production)

2. **HTTPS**: In production, ensure the admin panel is accessed via HTTPS

3. **Session Management**: JWT tokens expire after 24 hours (configurable via `JWT_EXPIRE_HOURS`)

4. **Self-Protection**: Users cannot delete their own accounts

5. **Audit Logging**: User creation, updates, and deletions are logged

## Troubleshooting

### Cannot Access Admin Panel

**Issue**: "Authentication required" error

**Solution**: 
- Ensure you're logged in
- Verify your user has "admin" role
- Check JWT token hasn't expired

### Cannot Create First Admin User

**Issue**: Database connection error

**Solution**:
```bash
# Check database is running
docker-compose ps postgres

# Verify DATABASE_URL environment variable
echo $DATABASE_URL

# Run initialization script
python init_admin_user.py
```

### Password Reset

**Issue**: Forgot admin password

**Solution**:
```bash
# Option 1: Use environment variables
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=newpassword
# Restart services

# Option 2: Database reset (if you have DB access)
docker-compose exec postgres psql -U podcast_user -d podcast_ai
# Then manually update user password hash
```

## Best Practices

1. **Create Individual Accounts**: Don't share admin credentials

2. **Use Strong Passwords**: Minimum 8 characters, use mix of letters, numbers, symbols

3. **Regular Audits**: Review user list periodically and remove inactive accounts

4. **Role Separation**: Use appropriate roles (don't make everyone admin)

5. **Backup**: Ensure database is backed up regularly

6. **Monitoring**: Check user login history for suspicious activity

## Migration from Environment Variables

If you're currently using environment variable authentication:

1. Run `python init_admin_user.py` to create database users
2. Log in with database credentials
3. Remove or change `ADMIN_PASSWORD` environment variable
4. Database authentication takes precedence

## Next Steps

- [User Roles and Permissions](./User-Roles.md)
- [Security Best Practices](../SECURITY.md)
- [System Administration](./README.md)
