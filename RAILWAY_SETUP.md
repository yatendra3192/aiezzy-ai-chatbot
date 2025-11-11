# Railway Persistent Storage Setup Instructions

## **Problem**
Every deployment to Railway wipes all user data, conversations, images, and videos because they're stored in the application directory.

## **Solution**
Configure Railway Persistent Volumes to store user data separately from application code.

## **Setup Steps**

### **1. Railway Dashboard Setup**

1. Go to your Railway project dashboard: https://railway.app
2. Navigate to your project: `aiezzy-ai-chatbot`
3. Click on **"Variables"** tab
4. Add environment variable:
   - **Name**: `RAILWAY_ENVIRONMENT`  
   - **Value**: `production`

### **2. Configure Persistent Volume**

1. In Railway dashboard, go to **"Settings"** tab
2. Scroll down to **"Volumes"** section
3. Click **"Add Volume"**
4. Configure:
   - **Mount Path**: `/app/data`
   - **Size**: `5GB` (or more based on your needs)
5. Click **"Add Volume"**

### **3. Deploy Updated Code**

The code changes have been made to:
- Store database at `/app/data/aiezzy_users.db`
- Store user uploads at `/app/data/uploads/`
- Store generated images at `/app/data/assets/`
- Store videos at `/app/data/videos/`
- Store conversations at `/app/data/conversations/`

Simply push your code and Railway will use the persistent volume.

## **File Structure After Setup**

```
Railway Container:
├── /app/                    # Application code (replaced on each deploy)
│   ├── web_app.py
│   ├── app.py
│   └── templates/
└── /app/data/              # PERSISTENT VOLUME (survives deployments)
    ├── aiezzy_users.db     # User accounts & sessions
    ├── uploads/            # User uploaded images
    ├── assets/             # Generated images
    ├── videos/             # Generated videos
    └── conversations/      # Chat history
        ├── 1/              # User ID folders
        ├── 2/
        └── default_user/
```

## **Benefits**

✅ **User accounts persist** across deployments
✅ **Chat history preserved** 
✅ **Generated images & videos saved**
✅ **No data loss** on code updates
✅ **Automatic backups** via Railway

## **Verification**

After setup:
1. Create a user account on aiezzy.com
2. Generate some images/videos
3. Deploy a code change
4. Verify user can still log in and see their content

## **Environment Variables Required**

```env
RAILWAY_ENVIRONMENT=production
OPENAI_API_KEY=sk-...
FAL_KEY=...
TAVILY_API_KEY=...
```

## **Local Development**

Local development continues to use local directories:
- `uploads/`, `assets/`, `videos/`, `conversations/`, `aiezzy_users.db`

Only production uses `/app/data/` persistent volume.