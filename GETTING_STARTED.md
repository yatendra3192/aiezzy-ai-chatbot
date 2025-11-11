# 🚀 Getting Started with Enhanced User Management

## ⚡ 3-Minute Quick Start

### Step 1: Run Setup Wizard (1 minute)

```bash
python setup.py
```

This will:
- ✅ Create `.env` file with auto-generated SECRET_KEY
- ✅ Check dependencies
- ✅ Initialize database
- ✅ Optionally create admin user

### Step 2: Add API Keys (1 minute)

Edit `.env` file and add your API keys:

```env
OPENAI_API_KEY=sk-your-key-here
FAL_KEY=your-fal-key-here
TAVILY_API_KEY=your-tavily-key-here
```

**Note:** Everything else is optional!

### Step 3: Start Application (1 minute)

```bash
python web_app.py
```

Visit: **http://localhost:5000**

🎉 **Done!** You now have a working app with enhanced user management!

---

## 🎯 What Works Out of the Box

### Without Additional Configuration

- ✅ **User registration** (email + password)
- ✅ **Login/logout**
- ✅ **Session management** (30-day sessions)
- ✅ **Usage quotas** (Free tier: 20 images, 5 videos, 100 messages/day)
- ✅ **Admin dashboard** (at `/admin`)
- ✅ **SQLite database** (zero configuration)
- ✅ **All AI features** (chat, image generation, video, etc.)

### With Optional Configuration

#### Email Features (Optional)

Add to `.env`:
```env
SENDGRID_API_KEY=SG.your-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
EMAIL_VERIFICATION_REQUIRED=true
```

Enables:
- ✉️ Email verification on signup
- 🔑 Password reset links
- 👋 Welcome emails

#### Social Login (Optional)

Add to `.env`:
```env
GOOGLE_CLIENT_ID=your-id
GOOGLE_CLIENT_SECRET=your-secret
GITHUB_CLIENT_ID=your-id
GITHUB_CLIENT_SECRET=your-secret
```

Enables:
- 🔐 "Sign in with Google"
- 🔐 "Sign in with GitHub"

---

## 📋 First-Time Setup Checklist

- [ ] Run `python setup.py`
- [ ] Edit `.env` with API keys (OPENAI, FAL, TAVILY)
- [ ] Create admin user (via setup wizard or manually)
- [ ] Start app: `python web_app.py`
- [ ] Test registration at http://localhost:5000
- [ ] Test admin dashboard at http://localhost:5000/admin
- [ ] (Optional) Configure SendGrid for emails
- [ ] (Optional) Configure OAuth for social login

---

## 🔧 Create Admin User

### During Setup

The setup wizard will ask if you want to create an admin user.

### Manually

```bash
python migrate_database.py create-admin admin admin@example.com password123
```

### What Admin Can Do

- View all users and statistics
- Manage user tiers (free → pro → enterprise)
- Activate/deactivate user accounts
- Monitor usage analytics
- View activity logs

Access at: **http://localhost:5000/admin**

---

## 🗄️ Database Options

### Development (Default)

**SQLite** - Already configured! No setup needed.

```
✅ File-based database
✅ Zero configuration
✅ Perfect for local development
```

### Production (Railway)

**PostgreSQL** - Add in Railway dashboard

```
1. Railway dashboard → Add PostgreSQL
2. DATABASE_URL auto-set
3. Deploy → automatic switch to PostgreSQL
```

---

## 🧪 Test Everything

### 1. Registration

```bash
curl -X POST http://localhost:5000/api/v2/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'
```

### 2. Login

```bash
curl -X POST http://localhost:5000/api/v2/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"test123"}'
```

### 3. Check Quota

```bash
curl http://localhost:5000/api/v2/quota/status \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

### 4. Admin Dashboard

Visit: http://localhost:5000/admin
Login with admin credentials

---

## 📊 Understanding Quotas

### Free Tier (Default for All Users)

| Resource | Daily Limit |
|----------|-------------|
| Images   | 20          |
| Videos   | 5           |
| Messages | 100         |

### Pro Tier

| Resource | Daily Limit |
|----------|-------------|
| Images   | 200         |
| Videos   | 50          |
| Messages | 1,000       |

### Customizing Quotas

Edit `.env`:

```env
QUOTA_FREE_IMAGES=20
QUOTA_FREE_VIDEOS=5
QUOTA_FREE_MESSAGES=100
```

Or upgrade users via admin dashboard.

---

## 🚂 Deploy to Railway

### Prerequisites

- Railway account
- GitHub repository

### Steps

1. **Add PostgreSQL**
   - Railway dashboard → New → Database → PostgreSQL
   - DATABASE_URL is auto-set

2. **Set Environment Variables**
   ```
   SECRET_KEY=<32-char-random-string>
   OPENAI_API_KEY=sk-...
   FAL_KEY=...
   TAVILY_API_KEY=...
   BASE_URL=https://yourdomain.com
   FLASK_ENV=production
   ```

3. **Deploy**
   ```bash
   git add .
   git commit -m "Enhanced user management"
   git push origin main
   ```

4. **Run Migration** (first time only)
   ```bash
   railway run python migrate_database.py migrate
   ```

5. **Create Admin**
   ```bash
   railway run python migrate_database.py create-admin admin admin@yourdomain.com secure123
   ```

✅ **Done!** Your app is live with PostgreSQL!

---

## 📁 Where Are Things Stored?

### Development (SQLite)

```
aiezzy-ai-chatbot-master/
├── aiezzy_users.db          # User database
├── conversations/           # Chat history
├── assets/                  # Generated images
├── videos/                  # Generated videos
└── uploads/                 # User uploads
```

### Production (Railway)

```
PostgreSQL Database:
├── Users
├── Sessions
├── OAuth Accounts
├── Usage Logs
└── Daily Usage Stats

Persistent Volume (/app/data):
├── conversations/
├── assets/
├── videos/
└── uploads/
```

---

## 🔍 Useful Commands

### Database

```bash
# Initialize database
python -c "from flask import Flask; from config import get_config; from models_v2 import init_db; app = Flask(__name__); app.config.from_object(get_config()); init_db(app)"

# Migrate from old database
python migrate_database.py migrate

# Create admin user
python migrate_database.py create-admin admin admin@example.com pass123
```

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python web_app.py

# Run setup wizard
python setup.py
```

### Testing

```bash
# Test API
curl http://localhost:5000/api/v2/quota/status

# Check database
sqlite3 aiezzy_users.db "SELECT * FROM users;"
```

---

## 🐛 Troubleshooting

### "No module named 'psycopg2'"

```bash
pip install psycopg2-binary
```

### "No module named 'config'"

Make sure all new files are in the project directory:
```bash
ls -la config.py models_v2.py api_routes.py
```

### Database Errors

```bash
# Start fresh
rm aiezzy_users.db
python setup.py
```

### Email Not Sending

Email features are optional! Without SendGrid:
- Email verification is disabled
- Password reset is disabled
- Registration and login still work normally

Set `EMAIL_VERIFICATION_REQUIRED=false` in `.env`

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| **GETTING_STARTED.md** (this file) | Quick start guide |
| **IMPLEMENTATION_SUMMARY.md** | What was implemented |
| **INTEGRATION_GUIDE.md** | How to integrate with existing code |
| **DEPLOYMENT_GUIDE.md** | Detailed deployment instructions |
| **USER_MANAGEMENT_README.md** | Complete feature documentation |

---

## ✨ What's New

### Before (Old System)

- Basic SQLite authentication
- Manual user management
- No quotas or limits
- No email verification
- No social login
- No admin dashboard

### After (Enhanced System)

- ✅ PostgreSQL support (production-ready)
- ✅ Email verification & password reset
- ✅ Google & GitHub OAuth login
- ✅ Usage quotas (images, videos, messages)
- ✅ Admin dashboard with analytics
- ✅ Tier system (free, pro, enterprise)
- ✅ Activity logging
- ✅ Session management
- ✅ Migration tools
- ✅ Comprehensive docs

---

## 🎯 Next Steps

### Today
1. ✅ Run `python setup.py`
2. ✅ Test locally at http://localhost:5000
3. ✅ Create admin user and test dashboard

### This Week
1. 📖 Read `INTEGRATION_GUIDE.md`
2. 🔧 Update `web_app.py` with new features
3. 📧 (Optional) Configure SendGrid
4. 🔐 (Optional) Configure OAuth

### This Month
1. 🚂 Deploy to Railway with PostgreSQL
2. 📊 Monitor usage via admin dashboard
3. 💰 (Optional) Add payment for Pro tier

---

## 🎉 You're Ready!

Everything is set up and ready to use. Just run:

```bash
python setup.py
python web_app.py
```

Then visit **http://localhost:5000**

For questions, check the documentation or review the implementation files.

**Happy coding! 🚀**
