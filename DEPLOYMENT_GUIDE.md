# 🚀 AIezzy Enhanced User Management - Deployment Guide

This guide will walk you through deploying the enhanced user management system with PostgreSQL, email verification, OAuth, and usage quotas.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Database Migration](#database-migration)
4. [Railway Deployment](#railway-deployment)
5. [SendGrid Email Setup](#sendgrid-email-setup)
6. [OAuth Setup](#oauth-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

## ✅ Prerequisites

- Python 3.9+
- Railway account (for production deployment)
- SendGrid account (for emails - optional but recommended)
- Google/GitHub OAuth apps (optional, for social login)

## 🔧 Local Development Setup

### 1. Install Dependencies

```bash
# Install all new dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# Minimum required:
# - OPENAI_API_KEY
# - FAL_KEY
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Initialize Database (Development)

For local development with SQLite:

```bash
# Run migration (if you have existing data)
python migrate_database.py migrate

# Or initialize fresh database
python -c "from web_app_v2 import app; from models_v2 import init_db; init_db(app)"
```

### 4. Create Admin User (Optional)

```bash
python migrate_database.py create-admin admin admin@yourdomain.com your-secure-password
```

### 5. Run Development Server

```bash
python web_app.py
```

Visit: http://localhost:5000

## 📊 Database Migration

### Migrating from Old SQLite Database

If you have existing user data in the old `aiezzy_users.db`:

```bash
python migrate_database.py migrate
```

This will:
- ✅ Create new enhanced schema
- ✅ Migrate all existing users
- ✅ Preserve passwords and sessions
- ✅ Migrate user activity logs
- ✅ Keep old database as backup

### Fresh Installation

If you're starting fresh:

```bash
# The database will auto-initialize on first run
python web_app.py
```

## 🚂 Railway Deployment

### Step 1: Add PostgreSQL Plugin

1. Go to your Railway project dashboard
2. Click "New" → "Database" → "Add PostgreSQL"
3. Railway will automatically set `DATABASE_URL` environment variable

### Step 2: Set Environment Variables

In Railway dashboard, add these variables:

**Required:**
```
SECRET_KEY=<generate-32-char-random-string>
OPENAI_API_KEY=sk-...
FAL_KEY=...
TAVILY_API_KEY=...
BASE_URL=https://aiezzy.com (or your domain)
FLASK_ENV=production
```

**Optional (Email Features):**
```
SENDGRID_API_KEY=SG....
SENDGRID_FROM_EMAIL=noreply@aiezzy.com
SENDGRID_FROM_NAME=AIezzy
EMAIL_VERIFICATION_REQUIRED=false
```

**Optional (OAuth):**
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

**Optional (Quotas - defaults shown):**
```
QUOTA_FREE_IMAGES=20
QUOTA_FREE_VIDEOS=5
QUOTA_FREE_MESSAGES=100
QUOTA_PRO_IMAGES=200
QUOTA_PRO_VIDEOS=50
QUOTA_PRO_MESSAGES=1000
```

### Step 3: Deploy

```bash
# Commit changes
git add .
git commit -m "feat: Enhanced user management with PostgreSQL"

# Push to Railway
git push origin main
```

Railway will automatically:
1. Install dependencies from requirements.txt
2. Run database migrations
3. Start the application with gunicorn

### Step 4: Run Migration (First Deploy)

If migrating existing data, run this in Railway's deployment logs or CLI:

```bash
python migrate_database.py migrate
```

### Step 5: Create Admin User

```bash
python migrate_database.py create-admin admin admin@yourdomain.com secure-password
```

## 📧 SendGrid Email Setup

### 1. Create SendGrid Account

- Go to [sendgrid.com](https://sendgrid.com)
- Sign up for free account (100 emails/day free)

### 2. Create API Key

1. Dashboard → Settings → API Keys
2. Create API Key with "Full Access"
3. Copy the key immediately (you won't see it again)

### 3. Verify Sender Identity

1. Dashboard → Settings → Sender Authentication
2. Verify your domain OR single sender email
3. Wait for verification email

### 4. Add to Environment

```bash
SENDGRID_API_KEY=SG.your-key-here
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=AIezzy
```

### Email Features

When configured, users will receive:
- ✉️ Email verification on signup (if enabled)
- 🔑 Password reset links
- 👋 Welcome emails

## 🔐 OAuth Setup

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable "Google+ API"
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs: `https://yourdomain.com/api/oauth/callback/google`
5. Copy Client ID and Client Secret

Add to `.env`:
```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. New OAuth App
3. Settings:
   - Homepage URL: `https://yourdomain.com`
   - Authorization callback URL: `https://yourdomain.com/api/oauth/callback/github`
4. Copy Client ID and Client Secret

Add to `.env`:
```
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

## 🧪 Testing

### Test Email Verification

```bash
# 1. Register new user
curl -X POST http://localhost:5000/api/v2/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 2. Check console for verification link (if SendGrid not configured)
# 3. Click link or make GET request to verify
```

### Test OAuth Login

1. Visit: `http://localhost:5000/api/oauth/login/google`
2. Complete Google login flow
3. Should redirect back to app with session

### Test Quotas

```bash
# Check quota status
curl http://localhost:5000/api/v2/quota/status \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

### Test Admin Dashboard

1. Create admin user (see above)
2. Login as admin
3. Visit: `http://localhost:5000/admin`

## 🔧 Troubleshooting

### Database Connection Errors

**PostgreSQL connection failed:**
```bash
# Check DATABASE_URL is set correctly
echo $DATABASE_URL

# Ensure psycopg2-binary is installed
pip install psycopg2-binary
```

### Email Not Sending

**SendGrid errors:**
```bash
# Check API key is valid
# Check sender email is verified in SendGrid dashboard
# Check logs for error messages
```

**Development workaround:**
```bash
# Disable email verification for local dev
EMAIL_VERIFICATION_REQUIRED=false
```

### OAuth Callback Errors

**Invalid redirect URI:**
- Ensure callback URL exactly matches in OAuth app settings
- Check BASE_URL is correct in environment
- Format: `{BASE_URL}/api/oauth/callback/{provider}`

### Migration Fails

**If migration script fails:**
```bash
# 1. Backup old database
cp aiezzy_users.db aiezzy_users.db.backup

# 2. Check database structure
sqlite3 aiezzy_users.db ".schema"

# 3. Try fresh database
rm aiezzy_users.db
python web_app.py  # Will create new database
```

### Import Errors

**Module not found:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --upgrade

# Check Python version
python --version  # Should be 3.9+
```

## 📊 Production Checklist

Before going live:

- [ ] PostgreSQL database configured
- [ ] All API keys set in environment
- [ ] SECRET_KEY is strong random string (32+ chars)
- [ ] BASE_URL points to your production domain
- [ ] FLASK_ENV=production
- [ ] SendGrid sender verified (if using email)
- [ ] OAuth redirect URIs point to production domain
- [ ] Admin user created
- [ ] Database backed up
- [ ] SSL certificate active (Railway handles this)
- [ ] Test all features work

## 🎉 Success!

Your enhanced AIezzy user management system is now live with:

- ✅ PostgreSQL database (scalable, production-ready)
- ✅ Email verification & password reset
- ✅ Google & GitHub OAuth login
- ✅ Usage tracking & quotas
- ✅ Admin dashboard
- ✅ Tier-based access control (free, pro, enterprise)

## 📞 Support

For issues:
1. Check this guide
2. Check application logs
3. Review Railway deployment logs
4. Check GitHub issues

## 🔄 Updates & Maintenance

### Updating Code

```bash
git pull origin main
pip install -r requirements.txt --upgrade
# Railway will auto-deploy
```

### Database Backups

**Railway PostgreSQL:**
- Automatic daily backups
- Manual backup via Railway CLI or dashboard

**Local SQLite:**
```bash
cp aiezzy_users.db aiezzy_users.db.backup-$(date +%Y%m%d)
```

### Monitoring

- Check Railway metrics dashboard
- Monitor SendGrid email sending stats
- Review admin dashboard for user activity

---

**Version:** 2.0
**Last Updated:** 2025
**Author:** AIezzy Development Team
