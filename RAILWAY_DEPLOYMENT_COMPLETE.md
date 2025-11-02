# 🚂 Complete Railway Deployment Guide - AIezzy Enhanced System

## 📋 Prerequisites

- ✅ Railway account (sign up at [railway.app](https://railway.app))
- ✅ GitHub account
- ✅ Git installed locally
- ✅ Your code pushed to GitHub

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Code (Local)

#### 1.1 Apply Integration Changes

```bash
# Navigate to your project
cd C:\Users\User\Desktop\aiezzy-ai-chatbot-master

# Option A: Use automated integration script (recommended)
python apply_integration.py

# Option B: Manual integration
# Open web_app_integration_patch.py and follow the instructions
```

#### 1.2 Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run setup
python setup.py

# Test the app
python web_app.py
```

Visit http://localhost:5000 and test:
- ✅ Registration works
- ✅ Login works
- ✅ AI features work
- ✅ Admin dashboard at `/admin`

#### 1.3 Commit Changes

```bash
git add .
git commit -m "feat: Add enhanced user management system with PostgreSQL support"
git push origin main
```

---

### Step 2: Create Railway Project

#### 2.1 Create New Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository: `aiezzy-ai-chatbot`
5. Click **"Deploy Now"**

Railway will start deploying, but we need to configure it first.

#### 2.2 Add PostgreSQL Database

1. In your Railway project, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway automatically creates the database and sets `DATABASE_URL` environment variable
3. Wait for PostgreSQL to be ready (green checkmark)

**Important:** Your app will automatically detect `DATABASE_URL` and use PostgreSQL instead of SQLite!

---

### Step 3: Configure Environment Variables

Click on your **web service** (not the database) → **Variables** tab

#### 3.1 Required Variables

Add these variables one by one:

```bash
# Flask Configuration
SECRET_KEY=<click "Generate" or use: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
BASE_URL=https://aiezzy.com
RAILWAY_ENVIRONMENT=production

# AI Service APIs (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key
FAL_KEY=your-fal-key
TAVILY_API_KEY=your-tavily-key
```

#### 3.2 Optional Variables (Email Features)

```bash
# SendGrid Email (Optional)
SENDGRID_API_KEY=SG.your-sendgrid-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=AIezzy
EMAIL_VERIFICATION_REQUIRED=false
```

#### 3.3 Optional Variables (OAuth Social Login)

```bash
# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth (Optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

#### 3.4 Optional Variables (Customize Quotas)

```bash
# Free Tier Limits (Optional - defaults shown)
QUOTA_FREE_IMAGES=20
QUOTA_FREE_VIDEOS=5
QUOTA_FREE_MESSAGES=100

# Pro Tier Limits (Optional)
QUOTA_PRO_IMAGES=200
QUOTA_PRO_VIDEOS=50
QUOTA_PRO_MESSAGES=1000
```

After adding variables, Railway will automatically redeploy.

---

### Step 4: Set Up Persistent Storage

Railway provides persistent volumes for file storage.

#### 4.1 Add Volume

1. Click on your web service
2. Go to **"Settings"** tab
3. Scroll to **"Volumes"**
4. Click **"+ New Volume"**
5. Mount Path: `/app/data`
6. Click **"Add"**

This ensures your uploaded files, videos, and images persist across deployments.

#### 4.2 Verify Volume

After deployment, your app will store files in:
- `/app/data/uploads/` - User uploads
- `/app/data/assets/` - Generated images
- `/app/data/videos/` - Generated videos
- `/app/data/documents/` - Document conversions
- `/app/data/conversations/` - Chat history

---

### Step 5: Connect Custom Domain (Optional)

#### 5.1 Add Domain in Railway

1. Click on your web service
2. Go to **"Settings"** tab
3. Scroll to **"Domains"**
4. Click **"+ Custom Domain"**
5. Enter: `aiezzy.com`

#### 5.2 Configure DNS

Railway will show you the CNAME or A record to add.

**For Cloudflare/GoDaddy:**
1. Add CNAME record:
   - Name: `@` (for root domain) or `www`
   - Value: `<your-railway-domain>.railway.app`
   - Proxy: Disabled (for Railway)

2. Wait for DNS propagation (5-30 minutes)

#### 5.3 Update BASE_URL

After domain is connected, update environment variable:
```bash
BASE_URL=https://aiezzy.com
```

#### 5.4 Update OAuth Redirect URIs

If using OAuth, update callback URLs in Google/GitHub:
- Google: `https://aiezzy.com/api/oauth/callback/google`
- GitHub: `https://aiezzy.com/api/oauth/callback/github`

---

### Step 6: Initialize Database & Admin User

#### 6.1 Run Migration (First Deploy Only)

Use Railway CLI or web terminal:

**Option A: Railway CLI**
```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migration
railway run python migrate_database.py migrate
```

**Option B: Via Deployment Logs**

If you have existing SQLite database locally:
1. Copy `aiezzy_users.db` to project root
2. Commit and push to GitHub
3. Railway will deploy
4. Database will auto-migrate on first run

#### 6.2 Create Admin User

```bash
# Via Railway CLI
railway run python migrate_database.py create-admin admin admin@yourdomain.com YourSecurePassword123

# Or add to your code as a one-time setup function
```

#### 6.3 Verify Admin Access

1. Visit: `https://aiezzy.com/admin`
2. Login with admin credentials
3. You should see the dashboard!

---

### Step 7: Verify Deployment

#### 7.1 Check Deployment Logs

1. Go to Railway project
2. Click on web service
3. Click **"Deployments"** tab
4. View latest deployment logs

Look for:
```
✅ Database initialized: postgresql://...
✅ Flask app started
✅ Gunicorn listening on 0.0.0.0:$PORT
```

#### 7.2 Test All Features

Visit your domain and test:

**Basic Auth:**
- ✅ User registration
- ✅ Login/logout
- ✅ Session persistence

**AI Features:**
- ✅ Chat with GPT-4o
- ✅ Image generation
- ✅ Video generation
- ✅ Image editing

**Quota System:**
- ✅ Quota displayed correctly
- ✅ Limits enforced
- ✅ Usage tracked

**Admin Dashboard:**
- ✅ Access at `/admin`
- ✅ View users
- ✅ View statistics
- ✅ Manage tiers

**Optional Features (if configured):**
- ✅ Email verification
- ✅ Password reset
- ✅ OAuth login (Google/GitHub)

---

## 📊 Monitoring & Maintenance

### Check Application Health

**Via Railway Dashboard:**
1. **Metrics** tab - CPU, Memory, Network usage
2. **Deployments** tab - Build and deployment history
3. **Logs** tab - Real-time application logs

**Via Admin Dashboard:**
```
https://yourdomain.com/admin
```
- Total users
- Active sessions
- Daily usage (images, videos, messages)
- Top users

### Database Backups

**PostgreSQL Backups (Automatic):**
- Railway automatically backs up PostgreSQL daily
- Access via Railway dashboard → PostgreSQL service → Backups

**Manual Backup:**
```bash
# Via Railway CLI
railway run pg_dump $DATABASE_URL > backup.sql
```

### Update Application

```bash
# Make changes locally
git add .
git commit -m "Update: Description of changes"
git push origin main

# Railway auto-deploys within 2-3 minutes
```

---

## 🔧 Troubleshooting

### Deployment Failed

**Check Logs:**
1. Railway dashboard → Deployments → View logs
2. Look for error messages

**Common Issues:**

**Missing Dependencies:**
```bash
# Ensure requirements.txt is up to date
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

**Import Errors:**
```
Error: No module named 'psycopg2'
```
**Fix:** Add to requirements.txt:
```
psycopg2-binary==2.9.9
```

**Database Connection Errors:**
```
Error: could not connect to database
```
**Fix:**
1. Verify PostgreSQL is running (green in Railway)
2. Check `DATABASE_URL` is set in environment variables
3. Restart deployment

### Application Won't Start

**Check Procfile:**
```bash
# Should be:
web: gunicorn web_app:web_app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload
```

**Check Python Version:**
```bash
# runtime.txt should have:
python-3.11.0
# or
python-3.11.9
```

### Email Not Sending

**Without SendGrid configured:**
- Email features are disabled (this is normal)
- Registration and login still work
- Set `EMAIL_VERIFICATION_REQUIRED=false`

**With SendGrid:**
1. Verify API key is correct
2. Verify sender email in SendGrid dashboard
3. Check SendGrid logs for errors

### OAuth Not Working

**Callback URL Mismatch:**
- Ensure OAuth app redirect URIs exactly match:
  - Google: `https://yourdomain.com/api/oauth/callback/google`
  - GitHub: `https://yourdomain.com/api/oauth/callback/github`
- Check `BASE_URL` environment variable

**Invalid State Token:**
- Ensure cookies are enabled
- Check session configuration

### Quota Not Tracking

**Check database connection:**
```python
# In Railway logs, look for:
"Database initialized: postgresql://..."
```

**Verify quota service initialized:**
- Should see quota records in `usage_logs` table
- Admin dashboard should show usage

---

## 🎯 Production Checklist

Before going fully live:

- [ ] PostgreSQL database added and connected
- [ ] All environment variables set
- [ ] Persistent volume added (`/app/data`)
- [ ] Database migration completed
- [ ] Admin user created and tested
- [ ] Custom domain connected (if applicable)
- [ ] SSL certificate active (Railway auto-provides)
- [ ] SendGrid verified (if using email)
- [ ] OAuth apps configured (if using social login)
- [ ] All features tested in production
- [ ] Monitoring set up (Railway metrics)
- [ ] Backups configured
- [ ] Error tracking reviewed

---

## 📈 Scaling Considerations

### When to Scale

**Signs you need more resources:**
- CPU usage consistently > 80%
- Memory usage consistently > 80%
- Response times increasing
- Request queue growing

### How to Scale on Railway

**Vertical Scaling (More Power):**
1. Railway dashboard → Service → Settings
2. Increase RAM/CPU allocation
3. Railway charges based on usage

**Horizontal Scaling (More Instances):**
```bash
# Update Procfile
web: gunicorn web_app:web_app --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --preload
```

Increase `--workers` based on CPU cores:
- 2 workers = 1-2 GB RAM
- 4 workers = 2-4 GB RAM
- 8 workers = 4-8 GB RAM

**Database Scaling:**
- Railway PostgreSQL auto-scales storage
- For high traffic, upgrade to larger PostgreSQL plan

---

## 💰 Cost Estimation

**Railway Pricing (as of 2024):**
- **Free Tier:** $5 credit/month
- **Hobby Plan:** $5/month + usage
- **Pro Plan:** $20/month + usage

**Typical costs for AIezzy:**
- Small site (< 1000 users): ~$10-20/month
- Medium site (< 10000 users): ~$30-50/month
- Large site (> 10000 users): ~$100+/month

**Cost breakdown:**
- PostgreSQL: ~$5/month
- Web service: ~$10-30/month (based on usage)
- Storage: ~$0.25/GB/month

**Optimization tips:**
- Use caching for frequently accessed data
- Optimize image sizes
- Clean up old files periodically
- Monitor and optimize database queries

---

## 🎉 Deployment Complete!

Your AIezzy application is now live on Railway with:

- ✅ Production PostgreSQL database
- ✅ Enhanced user management
- ✅ Email verification & password reset
- ✅ OAuth social login
- ✅ Usage quotas & analytics
- ✅ Admin dashboard
- ✅ Persistent file storage
- ✅ Auto-scaling capability
- ✅ Automatic backups
- ✅ SSL/HTTPS enabled
- ✅ Custom domain support

**Live at:** https://your-domain.com
**Admin at:** https://your-domain.com/admin

---

## 📞 Support & Resources

**Railway Documentation:**
- [Railway Docs](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)

**AIezzy Documentation:**
- `GETTING_STARTED.md` - Quick start guide
- `INTEGRATION_GUIDE.md` - Code integration
- `DEPLOYMENT_GUIDE.md` - Detailed deployment
- `USER_MANAGEMENT_README.md` - API documentation

**Need Help?**
1. Check Railway deployment logs
2. Check application logs in admin dashboard
3. Review integration patch file
4. Test locally first with `python web_app.py`

---

**Deployment Date:** $(date)
**Status:** 🚀 Ready for Production
**Next:** Monitor metrics and user feedback!
