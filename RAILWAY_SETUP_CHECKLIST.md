# 🚂 Railway Setup Checklist - AIezzy Enhanced System

## ✅ Code is Already Pushed to GitHub!

Your enhanced user management system is now on GitHub and ready for Railway deployment.

**Repository:** https://github.com/yatendra3192/aiezzy-ai-chatbot

---

## 📋 What You Need to Do on Railway

### Step 1: Add PostgreSQL Database (2 minutes)

1. Go to your Railway project dashboard
2. Click **"New"** button
3. Select **"Database"**
4. Choose **"Add PostgreSQL"**
5. Wait for it to turn green (ready)

✅ **Done!** Railway automatically sets `DATABASE_URL` environment variable.

---

### Step 2: Set Environment Variables (5 minutes)

Click on your **web service** → **Variables** tab

#### Required Variables (MUST SET):

```bash
SECRET_KEY=<click-generate-button-or-use-random-32-chars>
OPENAI_API_KEY=sk-your-key-here
FAL_KEY=your-key-here
TAVILY_API_KEY=your-key-here
BASE_URL=https://aiezzy.com
FLASK_ENV=production
```

**How to generate SECRET_KEY:**
- Click "Generate" button in Railway, OR
- Use: `python -c "import secrets; print(secrets.token_hex(32))"`

#### Optional Variables (Can add later):

**Email Features (SendGrid):**
```bash
SENDGRID_API_KEY=SG.your-key
SENDGRID_FROM_EMAIL=noreply@aiezzy.com
SENDGRID_FROM_NAME=AIezzy
EMAIL_VERIFICATION_REQUIRED=false
```

**OAuth Social Login:**
```bash
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
GITHUB_CLIENT_ID=your-id
GITHUB_CLIENT_SECRET=your-secret
```

**Custom Quotas (Optional):**
```bash
QUOTA_FREE_IMAGES=20
QUOTA_FREE_VIDEOS=5
QUOTA_FREE_MESSAGES=100
```

---

### Step 3: Configure Persistent Storage (1 minute)

1. Click on your web service
2. Go to **"Settings"** tab
3. Scroll to **"Volumes"**
4. Click **"+ New Volume"**
5. **Mount Path:** `/app/data`
6. Click **"Add"**

This ensures uploaded files and videos persist across deployments.

---

### Step 4: Deploy! (Railway auto-deploys)

Railway will automatically:
1. Detect the push to GitHub
2. Install dependencies from `requirements.txt`
3. Start the app using `Procfile`
4. Connect to PostgreSQL database

**Watch the deployment in:**
- **Deployments** tab → View logs
- Look for: "Database initialized: postgresql://..."

---

### Step 5: Run Database Migration (First time only - 2 minutes)

**Option A: Via Railway Web Terminal**

1. Click on your web service
2. Go to **"Settings"** tab
3. Scroll to **"Deploy"** section
4. Click **"Open Terminal"** (if available)
5. Run:
   ```bash
   python migrate_database.py migrate
   python migrate_database.py create-admin admin admin@aiezzy.com YourPassword123
   ```

**Option B: Via Railway CLI**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and link
railway login
railway link

# Run migration
railway run python migrate_database.py migrate
railway run python migrate_database.py create-admin admin admin@aiezzy.com YourPassword123
```

**Option C: Skip Migration (Fresh Start)**

If you don't have existing users to migrate, the database will auto-initialize on first run. Just create admin user:

```bash
railway run python migrate_database.py create-admin admin admin@aiezzy.com YourPassword123
```

---

### Step 6: Verify Everything Works (5 minutes)

#### Check Deployment Status

1. Go to **Deployments** tab
2. Latest deployment should be green (successful)
3. Click to view logs

**Look for these success messages:**
```
✅ Database initialized: postgresql://...
✅ Flask app started
✅ * Running on http://0.0.0.0:XXXX
```

#### Test Your Site

Visit your Railway URL (or custom domain):

**Test Registration:**
1. Click register
2. Create new account
3. Should work!

**Test Login:**
1. Login with your account
2. Session should persist

**Test AI Features:**
1. Chat with GPT-4o ✅
2. Generate image ✅
3. Check quota displays ✅

**Test Admin Dashboard:**
1. Visit: `https://yourdomain.com/admin`
2. Login with admin credentials
3. Should see dashboard! ✅

---

### Step 7: Connect Custom Domain (Optional - 5 minutes)

1. In Railway web service → **Settings** → **Domains**
2. Click **"+ Custom Domain"**
3. Enter: `aiezzy.com`
4. Railway shows you DNS records to add

**In GoDaddy/Cloudflare:**
1. Add CNAME record:
   - Name: `@` or `www`
   - Target: `your-app.railway.app`
2. Wait 5-30 minutes for DNS propagation

**Update Environment Variable:**
```bash
BASE_URL=https://aiezzy.com
```

**Update OAuth Callbacks (if using):**
- Google: `https://aiezzy.com/api/oauth/callback/google`
- GitHub: `https://aiezzy.com/api/oauth/callback/github`

---

## ✅ Success Checklist

- [ ] PostgreSQL database added (green checkmark)
- [ ] All required environment variables set
- [ ] Persistent volume mounted at `/app/data`
- [ ] Deployment successful (green)
- [ ] Database migration completed
- [ ] Admin user created
- [ ] Can access site at Railway URL
- [ ] Registration works
- [ ] Login works
- [ ] AI features work
- [ ] Admin dashboard accessible
- [ ] Custom domain connected (optional)
- [ ] SSL/HTTPS working automatically

---

## 🎯 Quick Reference

### Environment Variables Priority Order

**MUST HAVE (App won't work without these):**
1. `SECRET_KEY` - Session security
2. `OPENAI_API_KEY` - AI features
3. `FAL_KEY` - Image/video generation
4. `TAVILY_API_KEY` - Web search
5. `BASE_URL` - Your domain
6. `FLASK_ENV=production` - Production mode

**OPTIONAL (Nice to have):**
- SendGrid API key (email features)
- OAuth credentials (social login)
- Custom quotas (tier limits)

### Database Setup

**Railway automatically provides:**
- `DATABASE_URL` - PostgreSQL connection string

**You don't need to set:**
- Database host, port, username, password
- Railway handles all of this automatically!

### Migration Commands

```bash
# Migrate existing data
railway run python migrate_database.py migrate

# Create admin user
railway run python migrate_database.py create-admin username email password

# Example
railway run python migrate_database.py create-admin admin admin@aiezzy.com MySecurePass123
```

---

## 🆘 Troubleshooting

### Deployment Failed

**Check deployment logs:**
1. Deployments tab → Click failed deployment
2. Read error message

**Common issues:**

**"No module named 'psycopg2'"**
- Should auto-install from requirements.txt
- If not, Railway may need rebuild
- Solution: Make a small commit to trigger rebuild

**"Database connection failed"**
- Check PostgreSQL is running (green)
- Check `DATABASE_URL` is set
- Solution: Restart deployment

**"ImportError: cannot import..."**
- Missing dependency
- Solution: Check requirements.txt and redeploy

### Application Won't Start

**Check these:**
1. `Procfile` exists and correct
2. Python version in `runtime.txt`
3. All files committed to GitHub
4. Environment variables set

### Email Not Working

**Without SendGrid:**
- Email features are disabled (this is OK!)
- Set: `EMAIL_VERIFICATION_REQUIRED=false`
- Registration and login still work normally

**With SendGrid:**
- Verify API key is correct
- Verify sender email in SendGrid dashboard
- Check SendGrid activity logs

### OAuth Errors

**"Invalid redirect URI"**
- Update OAuth app settings with exact callback URL
- Google: `https://yourdomain.com/api/oauth/callback/google`
- GitHub: `https://yourdomain.com/api/oauth/callback/github`
- Must be HTTPS in production

---

## 📊 Monitoring

### Check Application Health

**Railway Dashboard:**
- **Metrics** tab - CPU, Memory, Network
- **Deployments** - Build history
- **Logs** - Real-time logs

**Admin Dashboard:**
```
https://yourdomain.com/admin
```
- Total users
- Active sessions
- Daily usage stats
- User management

---

## 🎉 You're Done!

Once all checkboxes above are complete:

✅ Your AIezzy app is live on Railway with:
- Production PostgreSQL database
- Enhanced user management
- Email verification system
- OAuth social login
- Usage quotas & analytics
- Admin dashboard
- Custom domain (optional)
- SSL/HTTPS automatic

**Admin Dashboard:** https://yourdomain.com/admin
**Main App:** https://yourdomain.com

---

## 📞 Need Help?

**Check Railway logs first:**
- Deployments tab → View logs
- Look for error messages

**Review documentation:**
- `RAILWAY_DEPLOYMENT_COMPLETE.md` - Full guide
- `USER_MANAGEMENT_README.md` - API docs
- `GETTING_STARTED.md` - Quick start

**Railway Support:**
- [Railway Docs](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)

---

**Status:** ✅ Code pushed to GitHub, ready for Railway!
**Next:** Follow this checklist in Railway dashboard
**Time:** 15-20 minutes total
