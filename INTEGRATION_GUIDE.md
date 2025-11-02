# 🔧 Integration Guide - Enhanced User Management

This guide explains how to integrate the new enhanced user management system into your existing `web_app.py`.

## 📋 Quick Start (Recommended)

### Option 1: Fresh Integration (Easiest)

Create a new enhanced `web_app.py` with all features integrated:

```python
# At the top of web_app.py, add these imports:

from config import get_config
from models_v2 import db, init_db, User
from api_routes import api as api_v2
from quota_service import quota_service

# Replace config section with:
config = get_config()
web_app.config.from_object(config)

# Initialize database (add after Flask app creation):
init_db(web_app)

# Register new API routes:
web_app.register_blueprint(api_v2)

# Add admin dashboard route:
@web_app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')
```

### Option 2: Gradual Migration

Keep existing system running while adding new features:

1. Both old and new systems can coexist
2. New users use enhanced system (v2 APIs)
3. Existing users continue with old system
4. Migrate when ready

## 📝 Step-by-Step Integration

### Step 1: Update Imports

Add to the top of `web_app.py`:

```python
# Enhanced user management
from config import get_config
from models_v2 import db, init_db
from api_routes import api as api_v2
from quota_service import quota_service
from email_service import email_service
from oauth_service import oauth_service
```

### Step 2: Update Flask Configuration

Replace the config section (around line 18-40):

```python
# Get configuration
config = get_config()

# Apply configuration to Flask app
web_app.config.from_object(config)

# Configure directories (keep existing logic, update paths)
if os.environ.get('RAILWAY_ENVIRONMENT'):
    DATA_DIR = '/app/data'
else:
    DATA_DIR = '.'

# Update paths using config
web_app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
ASSETS_DIR = config.ASSETS_DIR
VIDEOS_DIR = config.VIDEOS_DIR
# ... etc
```

### Step 3: Initialize Enhanced Database

Add after Flask app configuration:

```python
# Initialize enhanced database with SQLAlchemy
init_db(web_app)

# Keep old user_manager for backward compatibility if needed
user_manager = UserManager()  # Old system
```

### Step 4: Register New API Routes

Add after existing route definitions:

```python
# Register enhanced API routes
web_app.register_blueprint(api_v2)
```

### Step 5: Add Admin Dashboard Route

```python
@web_app.route('/admin')
@admin_required
def admin_dashboard_page():
    """Admin dashboard"""
    return render_template('admin_dashboard.html')
```

### Step 6: Add Quota Checking to AI Endpoints

Update your `/api/chat` and `/api/analyze-image` endpoints:

```python
@web_app.route('/api/chat', methods=['POST'])
@optional_auth
def chat():
    """Enhanced chat endpoint with quota checking"""

    # Get current user
    user = get_current_user()
    user_id = user['id'] if user else None

    # Check quota before processing
    quota_check = quota_service.check_quota(user_id, 'message')
    if not quota_check['allowed']:
        return jsonify({
            'error': quota_check['message'],
            'quota_exceeded': True,
            'remaining': quota_check['remaining'],
            'limit': quota_check['limit']
        }), 429  # Too Many Requests

    # ... existing chat logic ...

    # Log usage after successful completion
    quota_service.log_usage(user_id, 'message', 1)

    return jsonify(response)
```

Similar pattern for image and video generation:

```python
# Before generating image/video
quota_check = quota_service.check_quota(user_id, 'image')  # or 'video'
if not quota_check['allowed']:
    return jsonify({'error': quota_check['message']}), 429

# After successful generation
quota_service.log_usage(user_id, 'image', 1)  # or 'video'
```

### Step 7: Update Frontend (modern_chat.html)

Add quota display and OAuth buttons to your chat interface.

**Add to HTML (in sidebar or header):**

```html
<!-- Quota Status Display -->
<div class="quota-status" id="quotaStatus" style="display: none;">
    <h3>Today's Usage</h3>
    <div class="quota-item">
        <span>Images: <span id="quotaImages">0</span>/<span id="quotaImagesLimit">20</span></span>
        <div class="quota-bar">
            <div class="quota-fill" id="quotaImagesBar"></div>
        </div>
    </div>
    <div class="quota-item">
        <span>Videos: <span id="quotaVideos">0</span>/<span id="quotaVideosLimit">5</span></span>
        <div class="quota-bar">
            <div class="quota-fill" id="quotaVideosBar"></div>
        </div>
    </div>
    <div class="quota-item">
        <span>Messages: <span id="quotaMessages">0</span>/<span id="quotaMessagesLimit">100</span></span>
        <div class="quota-bar">
            <div class="quota-fill" id="quotaMessagesBar"></div>
        </div>
    </div>
</div>

<!-- OAuth Login Buttons (in login form) -->
<div class="oauth-buttons">
    <button onclick="loginWithOAuth('google')" class="oauth-btn google-btn">
        <img src="/static/google-icon.png" /> Continue with Google
    </button>
    <button onclick="loginWithOAuth('github')" class="oauth-btn github-btn">
        <img src="/static/github-icon.png" /> Continue with GitHub
    </button>
</div>
```

**Add to JavaScript:**

```javascript
// Load quota status
async function loadQuotaStatus() {
    try {
        const response = await fetch('/api/v2/quota/status', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('session_token')}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateQuotaDisplay(data);
        }
    } catch (error) {
        console.error('Failed to load quota:', error);
    }
}

function updateQuotaDisplay(quota) {
    // Update images
    document.getElementById('quotaImages').textContent = quota.usage.image || 0;
    document.getElementById('quotaImagesLimit').textContent = quota.limits.images || 0;
    const imagePercent = ((quota.usage.image || 0) / (quota.limits.images || 1)) * 100;
    document.getElementById('quotaImagesBar').style.width = imagePercent + '%';

    // Similar for videos and messages
    // ...

    document.getElementById('quotaStatus').style.display = 'block';
}

// OAuth login
function loginWithOAuth(provider) {
    window.location.href = `/api/oauth/login/${provider}`;
}

// Call on page load
document.addEventListener('DOMContentLoaded', function() {
    loadQuotaStatus();
});
```

## 🎨 UI Enhancements

### Add Quota Warning Messages

```javascript
// Show warning when quota is low
function checkQuotaAndWarn(type) {
    const quota = getCurrentQuota();  // Get from state
    const remaining = quota.remaining[type];
    const limit = quota.limits[type];

    if (remaining <= 0) {
        showMessage(`Daily ${type} limit reached! Upgrade to Pro for more.`, 'error');
        return false;
    } else if (remaining <= limit * 0.2) {  // 20% remaining
        showMessage(`Warning: Only ${remaining} ${type}s remaining today.`, 'warning');
    }
    return true;
}

// Use before API calls
if (!checkQuotaAndWarn('image')) {
    return;  // Don't proceed
}
```

### Add Tier Badge

```html
<!-- Show user's tier -->
<div class="user-tier-badge">
    <span class="tier-label" id="userTier">Free</span>
    <a href="/upgrade" class="upgrade-link">Upgrade to Pro</a>
</div>
```

## 🔄 Migration Paths

### Path 1: Complete Switch (Recommended for Railway)

1. Deploy all new files
2. Add PostgreSQL to Railway
3. Run migration script
4. Switch to new API routes
5. Test thoroughly
6. Remove old models.py and auth.py

### Path 2: Hybrid (For Testing)

1. Deploy new files alongside old
2. Keep both databases temporarily
3. New users → v2 system
4. Old users → old system (or migrate gradually)
5. Eventually switch completely

## ✅ Testing Checklist

After integration, test:

- [ ] User registration (v2 API)
- [ ] Email verification (if enabled)
- [ ] Login with email/password
- [ ] OAuth login (Google, GitHub)
- [ ] Password reset flow
- [ ] Quota display shows correctly
- [ ] Quota limits are enforced
- [ ] AI features work with quota tracking
- [ ] Admin dashboard accessible
- [ ] Admin can manage users
- [ ] Old users can still login (if using hybrid)

## 🐛 Common Issues

### Database Connection

**Error:** `No module named 'psycopg2'`

**Fix:**
```bash
pip install psycopg2-binary
```

### Import Errors

**Error:** `ImportError: cannot import name 'config'`

**Fix:** Ensure all new files are in the same directory as `web_app.py`

### API Routes Conflict

**Error:** Routes returning old data

**Fix:** Ensure `api_v2` blueprint is registered:
```python
web_app.register_blueprint(api_v2)
```

### Session Token Not Working

**Fix:** Update frontend to use new auth format:
```javascript
headers: {
    'Authorization': `Bearer ${localStorage.getItem('session_token')}`
}
```

## 📊 Performance Considerations

### Database Connection Pooling

PostgreSQL automatically pools connections. For SQLite in dev:

```python
# config.py already handles this
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
}
```

### Quota Caching

For high traffic, consider caching quota status:

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_cached_quota(user_id, hour):
    """Cache quota for 1 hour"""
    return quota_service.get_user_quota_status(user_id)

# Use in route:
current_hour = datetime.now().hour
quota = get_cached_quota(user_id, current_hour)
```

## 🎉 Next Steps

After successful integration:

1. **Configure SendGrid** for email features
2. **Set up OAuth** apps for social login
3. **Customize quotas** for your business model
4. **Create upgrade flow** for Pro tier
5. **Add payment processing** (Stripe, etc.)
6. **Monitor usage** via admin dashboard
7. **Scale database** as needed on Railway

## 📞 Need Help?

- Check `DEPLOYMENT_GUIDE.md` for detailed setup
- Review example code in `api_routes.py`
- Test with `migrate_database.py` script
- Check Railway logs for errors

---

**Integration Complete! 🚀**

Your AIezzy app now has:
- ✅ Production-grade PostgreSQL database
- ✅ Email verification & password reset
- ✅ Google & GitHub OAuth
- ✅ Usage tracking & quotas
- ✅ Admin dashboard
- ✅ Scalable architecture
