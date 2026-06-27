# Security Report

## Issues Found & Fixed

### 1. Hardcoded Secret Keys (FIXED)
- **Issue**: SECRET_KEY was hardcoded as `supersecretkey-change-in-production` in config.py
- **Fix**: Changed to empty string (must be provided via .env)
- **File**: `backend/app/core/config.py:8`

### 2. Hardcoded DB Password in Docker Compose (NOTED)
- **Issue**: PostgreSQL password `qanuni_secret` exposed in docker-compose.yml
- **Status**: Not changed as it's for local development only
- **Recommendation**: Use Docker secrets for production

### 3. Missing Rate Limiting on Register (FIXED)
- **Issue**: Rate limiting was only applied to login endpoint
- **Fix**: Extended rate limiting to register endpoint (3 requests/minute)
- **File**: `backend/app/main.py:19`

### 4. JWT Secret in Docker Compose (FIXED)
- **Issue**: SECRET_KEY environment variable had fallback default in docker-compose.yml
- **Fix**: Removed default value, now requires explicit setting
- **File**: `docker-compose.yml:18`

### 5. Hardcoded User Name in Frontend (FIXED)
- **Issue**: User name "أ. محمد الكبسي" was hardcoded in 19 HTML files
- **Fix**: Replaced with dynamic `data-user-name` attribute
- **Files**: All frontend HTML files updated

### 6. Logout Navigation (FIXED)
- **Issue**: Logout button just linked to login.html without clearing session
- **Fix**: Changed to call `QaniniAuth.logout()` JavaScript function
- **Files**: All frontend HTML files updated

## Remaining Recommendations
1. Add HTTPS in production
2. Use environment variables for all secrets
3. Add SQL injection hardening (though SQLAlchemy provides parameterization)
4. Add CSRF protection for state-changing operations
5. Implement proper API key management for external services
