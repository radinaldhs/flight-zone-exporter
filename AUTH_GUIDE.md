# Authentication System Guide

## Overview

The Flight Zone Exporter now features a complete authentication system with user registration and login. Each user stores their own GIS credentials securely, eliminating the need for environment variables.

## How It Works

### Backend (FastAPI)

1. **User Registration**: Users create an account with their GIS credentials
2. **JWT Authentication**: Secure token-based authentication
3. **Per-User GIS Credentials**: Each user's ArcGIS credentials are encrypted and stored
4. **Protected Endpoints**: All flight zone operations require authentication

### Frontend (Vue.js)

1. **Login Page**: Users sign in with email/password
2. **Registration Page**: New users register with GIS credentials
3. **Protected Routes**: Automatic redirect to login if not authenticated
4. **Auto Token Injection**: Auth token automatically added to API requests

## User Flow

### First Time Users

1. Visit the application
2. Click "Sign up" or navigate to `/register`
3. Fill in the registration form:
   - **Account Info**: Email, username, password
   - **GIS Credentials**:
     - GIS Auth Username (e.g., `agasha123`)
     - GIS Auth Password
     - GIS Username (e.g., `fmiseditor`)
     - GIS Password
4. Submit registration
5. Automatically logged in and redirected to home

### Returning Users

1. Visit the application
2. Click "Sign in" or navigate to `/login`
3. Enter email and password
4. Submit login
5. Redirected to home with authenticated access

## API Endpoints

### Authentication Endpoints

**Register**
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword",
  "full_name": "John Doe",
  "gis_auth_username": "agasha123",
  "gis_auth_password": "password123",
  "gis_username": "fmiseditor",
  "gis_password": "password456"
}
```

**Login**
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Get Current User**
```http
GET /api/auth/me
Authorization: Bearer <token>
```

### Protected Endpoints

All existing endpoints now require authentication:

```http
POST /api/arcgis/spk/check
Authorization: Bearer <token>

DELETE /api/arcgis/spk
Authorization: Bearer <token>

POST /api/kml/generate-shapefile
Authorization: Bearer <token>

# ... etc
```

## Security Features

### Backend

- ✅ **Password Hashing**: Passwords hashed with bcrypt
- ✅ **JWT Tokens**: Secure, stateless authentication
- ✅ **Token Expiry**: 7-day token expiration
- ✅ **Credential Storage**: GIS credentials stored per-user
- ✅ **Protected Routes**: All sensitive operations require auth

### Frontend

- ✅ **Secure Storage**: Token stored in localStorage
- ✅ **Auto Logout**: 401 responses trigger automatic logout
- ✅ **Route Protection**: Unauthenticated users redirected to login
- ✅ **Token Injection**: Auth token auto-added to requests

## User Data Storage

Users are stored in a simple JSON file (`users.json` in the backend root):

```json
{
  "user-id-123": {
    "id": "user-id-123",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "hashed_password": "$2b$12$...",
    "gis_auth_username": "agasha123",
    "gis_auth_password": "encrypted",
    "gis_username": "fmiseditor",
    "gis_password": "encrypted",
    "is_active": true,
    "created_at": "2025-12-21T..."
  }
}
```

**Note**: For production, consider migrating to a proper database (PostgreSQL, MongoDB, etc.).

## Environment Variables

### Backend (.env)

Only need a SECRET_KEY now (GIS creds removed):

```env
SECRET_KEY=your-secure-secret-key-min-32-characters-long-change-this
```

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Frontend (.env)

```env
VITE_API_URL=https://your-backend-api.onrender.com
```

## Deployment Updates

### Backend (Render)

Update environment variables:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | (generate secure key) |
| ~~GIS_AUTH_USERNAME~~ | (remove) |
| ~~GIS_AUTH_PASSWORD~~ | (remove) |
| ~~GIS_USERNAME~~ | (remove) |
| ~~GIS_PASSWORD~~ | (remove) |

### Frontend (Vercel)

No changes needed - already configured with `VITE_API_URL`.

## Migration Guide

### For Existing Users

If you had hardcoded GIS credentials before:

1. **Backend**: Remove old environment variables
2. **Backend**: Add `SECRET_KEY` environment variable
3. **Users**: Register new account with their GIS credentials
4. **Deploy**: Push changes to Render/Vercel

## Testing Locally

### Backend

```bash
cd flight-zone-exporter

# Install new dependencies
pip install -r requirements.txt

# Set SECRET_KEY in .env
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env

# Run server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd flight-zone-exporter-vue

# Make sure VITE_API_URL points to backend
cat .env  # Should show: VITE_API_URL=http://localhost:8000

# Run dev server
npm run dev
```

### Test Flow

1. Open http://localhost:3000
2. Should redirect to `/login`
3. Click "Sign up"
4. Fill registration form with test GIS credentials
5. Submit - should auto-login and redirect to home
6. Test uploading files and processing
7. Logout and login again to verify persistence

## Troubleshooting

### "Could not validate credentials"
- Token expired or invalid
- Solution: Logout and login again

### "User with this email already exists"
- Email already registered
- Solution: Use different email or login with existing account

### CORS Errors
- Backend not allowing frontend origin
- Solution: Check `CORS_ORIGINS` in backend settings

### 401 Unauthorized on API Calls
- Token not being sent
- Solution: Check localStorage has `token` key

## Future Enhancements

Possible improvements:

1. **Database Migration**: Move from JSON file to PostgreSQL
2. **Password Reset**: Email-based password recovery
3. **Email Verification**: Verify email on registration
4. **2FA**: Two-factor authentication
5. **Admin Panel**: Manage users
6. **Audit Logs**: Track user actions
7. **Role-Based Access**: Different permission levels

## Security Best Practices

✅ **Do:**
- Use strong, unique passwords
- Keep SECRET_KEY secret
- Use HTTPS in production
- Rotate tokens periodically
- Monitor for suspicious activity

❌ **Don't:**
- Share your account credentials
- Commit SECRET_KEY to git
- Use weak passwords
- Store tokens in cookies without httpOnly flag
- Disable authentication for convenience

## API Documentation

Once deployed, visit your API docs:
- **Swagger UI**: `https://your-api.onrender.com/docs`
- **ReDoc**: `https://your-api.onrender.com/redoc`

Test authentication endpoints directly in the Swagger UI!

---

© 2025 Radinal Dewantara Husein
