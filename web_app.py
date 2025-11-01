from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import os
import sys
import base64
import uuid
import time
import json
import secrets
import requests
from werkzeug.utils import secure_filename
from app import app as langgraph_app, encode_image_to_content_block, set_recent_image_path, clear_thread_cache, clear_thread_context, reset_all_context, set_current_thread_id, set_document_context, update_document_latest, add_uploaded_file, get_latest_uploaded_file, get_unified_file_context

# Import authentication modules
from models import UserManager
from auth import login_required, admin_required, optional_auth, get_current_user, get_user_id, create_session, clear_session, get_client_ip, get_user_agent, rate_limit_check, validate_password_strength, sanitize_username, is_valid_email, init_auth

# Initialize Flask app
web_app = Flask(__name__)

# Configure persistent storage paths for Railway
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production: Use Railway persistent volume
    DATA_DIR = '/app/data'
    web_app.config['UPLOAD_FOLDER'] = f'{DATA_DIR}/uploads'
    ASSETS_DIR = f'{DATA_DIR}/assets'
    VIDEOS_DIR = f'{DATA_DIR}/videos'
    DOCUMENTS_DIR = f'{DATA_DIR}/documents'
    CONVERSATIONS_DIR = f'{DATA_DIR}/conversations'
    DATABASE_PATH = f'{DATA_DIR}/aiezzy_users.db'
else:
    # Development: Use local directories
    DATA_DIR = '.'
    web_app.config['UPLOAD_FOLDER'] = 'uploads'
    ASSETS_DIR = 'assets'
    VIDEOS_DIR = 'videos'
    DOCUMENTS_DIR = 'documents'
    CONVERSATIONS_DIR = 'conversations'
    DATABASE_PATH = 'aiezzy_users.db'

web_app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size (increased for documents)

# Create directories if they don't exist
os.makedirs(web_app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

# Initialize authentication
init_auth(web_app)

# Initialize user manager
user_manager = UserManager()

# ===== Security Headers for A+ Rating =====
@web_app.after_request
def add_security_headers(response):
    """
    Add comprehensive security headers to all responses for A+ security rating.
    These headers protect against XSS, clickjacking, MIME sniffing, and other attacks.
    """
    # HSTS - Force HTTPS for 1 year, including subdomains
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # CSP - Strict Content Security Policy (prevent XSS)
    # Allow same-origin resources, inline styles/scripts (needed for app), external CDNs
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://www.google-analytics.com; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp_policy

    # X-Frame-Options - Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # X-Content-Type-Options - Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # X-XSS-Protection - Enable XSS filter (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Referrer-Policy - Control referer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions-Policy - Disable unnecessary browser features
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # Cache-Control - Enable browser caching for static assets (Core Web Vitals optimization)
    if request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'  # 1 year
    elif request.path.endswith(('.css', '.js')):
        response.headers['Cache-Control'] = 'public, max-age=2592000'  # 30 days
    elif request.path.endswith(('.html', '.txt')):
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 day
    else:
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour

    return response

# Add custom filter for timestamp formatting
@web_app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    import datetime
    try:
        dt = datetime.datetime.fromtimestamp(float(timestamp))
        now = datetime.datetime.now()
        diff = now - dt
        
        # For file browser, show relative time
        if diff.days == 0:
            if diff.seconds < 3600:
                return f"{diff.seconds // 60}m ago"
            else:
                return f"{diff.seconds // 3600}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return 'Unknown date'

# Add file type filter for file browser
@web_app.template_filter('get_file_type')
def get_file_type(filename):
    """Get file type for styling"""
    if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return 'image'
    elif filename.endswith('.mp4'):
        return 'video'
    elif filename.endswith('.json'):
        return 'json'
    else:
        return 'file'

# Add custom filter to process image paths in shared content
@web_app.template_filter('process_shared_content')
def process_shared_content(content):
    """Process content for shared conversations, ensuring images display properly"""
    import re
    if not content:
        return content
    
    # The content should already have proper HTML image tags from the conversation
    # Just ensure the paths are working - they should be relative paths like /assets/img_123.png
    # which will be served by our asset routes
    
    # Make sure any asset paths are properly formatted
    content = re.sub(r'src=["\']/?assets/', r'src="/assets/', content)
    content = re.sub(r'src=["\']/?uploads/', r'src="/uploads/', content)
    content = re.sub(r'src=["\']/?videos/', r'src="/videos/', content)
    
    return content

# Create upload directory
os.makedirs('uploads', exist_ok=True)
os.makedirs('assets', exist_ok=True)
os.makedirs('videos', exist_ok=True)
os.makedirs('shared', exist_ok=True)
os.makedirs('feature_requests', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'heif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'csv', 'txt', 'html', 'htm', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'heif'}

# Store recent images for editing reference
recent_images = {}
# Store the most recent image per thread for editing context
thread_image_context = {}
# Store document context per thread for operations (tracks both original upload and conversions)
# Structure: {
#   'original': {'path': '...', 'filename': '...', 'timestamp': ...},  # Never overwritten
#   'latest': {'path': '...', 'filename': '...', 'timestamp': ...}     # Updated with each conversion
# }
thread_document_context = {}
# Store shared conversations
shared_conversations = {}
# Store feature requests
feature_requests = {}
# Store user conversations persistently
user_conversations = {}

# Conversations directory already created above with CONVERSATIONS_DIR

# ===== Permanent File Links System =====
# Store permanent files with short unique IDs
PERMANENT_FILES_DIR = os.path.join(DATA_DIR, 'permanent_files')
PERMANENT_FILES_DB = os.path.join(DATA_DIR, 'permanent_files.json')
os.makedirs(PERMANENT_FILES_DIR, exist_ok=True)

def load_permanent_files_db():
    """Load the permanent files database"""
    if os.path.exists(PERMANENT_FILES_DB):
        try:
            with open(PERMANENT_FILES_DB, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_permanent_files_db(db):
    """Save the permanent files database"""
    with open(PERMANENT_FILES_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2)

def generate_short_id(length=12):
    """Generate a short unique ID for permanent files"""
    import string
    import random
    chars = string.ascii_lowercase + string.digits
    while True:
        short_id = ''.join(random.choice(chars) for _ in range(length))
        db = load_permanent_files_db()
        if short_id not in db:
            return short_id

# ===== IndexNow Protocol for Instant Search Engine Indexing =====
INDEXNOW_KEY = "dc42f34e7a2e52048e3d62723b7193017d5f13cc23ca4322b9ebb5e2e2ada103"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/IndexNow"

def submit_to_indexnow(urls):
    """
    Submit URLs to IndexNow for instant indexing in Bing, Yandex, and other search engines.

    Args:
        urls: Single URL string or list of URLs to submit

    Returns:
        bool: True if submission successful, False otherwise
    """
    if not urls:
        return False

    # Convert single URL to list
    if isinstance(urls, str):
        urls = [urls]

    # Prepare payload
    payload = {
        "host": "aiezzy.com",
        "key": INDEXNOW_KEY,
        "urlList": urls
    }

    try:
        response = requests.post(
            INDEXNOW_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=10
        )

        if response.status_code in [200, 202]:
            print(f"[SUCCESS] IndexNow: Successfully submitted {len(urls)} URL(s)")
            return True
        else:
            print(f"[WARNING] IndexNow: Got status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] IndexNow: Error - {str(e)}")
        return False

def submit_key_pages_to_indexnow():
    """Submit all key landing pages to IndexNow for instant indexing"""
    key_pages = [
        "https://aiezzy.com/",
        "https://aiezzy.com/pdf-converter",
        "https://aiezzy.com/ai-image-generator",
        "https://aiezzy.com/word-to-pdf",
        "https://aiezzy.com/chatgpt-alternative",
        "https://aiezzy.com/text-to-video",
        "https://aiezzy.com/pdf-to-word",
        "https://aiezzy.com/excel-to-pdf",
        "https://aiezzy.com/pdf-to-excel",
        "https://aiezzy.com/compress-pdf",
        "https://aiezzy.com/merge-pdf"
    ]
    return submit_to_indexnow(key_pages)

def allowed_file(filename):
    # Accept all file types for images
    return '.' in filename

def allowed_document(filename):
    # Accept all file types for documents
    return '.' in filename

def detect_multi_step_request(message, history):
    """Detect if this is a multi-step request"""
    message_lower = message.lower()
    task_indicators = [
        ['news', 'latest', 'current'],
        ['create', 'generate', 'image'],
        ['write', 'post', 'linkedin'],
        ['edit', 'modify', 'change']
    ]
    
    matched_tasks = sum(1 for indicators in task_indicators if any(word in message_lower for word in indicators))
    return matched_tasks > 1

def determine_current_step(message, history):
    """Determine which step of a multi-step process we're on"""
    if not history:
        return 1
    
    # Count previous steps based on assistant responses
    step_count = 1
    for msg in history:
        if msg.get('role') == 'assistant' and any(indicator in msg.get('content', '') for indicator in ['Step 1', 'Step 2', 'Next:', 'Now I\'ll']):
            step_count += 1
    
    return min(step_count, 3)  # Cap at 3 steps

def get_step_context(history):
    """Get context from previous steps to inform current action"""
    if not history:
        return None
    
    # Look for previous search results or image generation
    recent_context = []
    for msg in reversed(history[-4:]):  # Check last 4 messages
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if 'Web Search Results' in content:
                recent_context.append("Previous step: Web search completed with news results")
            elif 'Image saved to' in content or '<img' in content:
                recent_context.append("Previous step: Image generation/editing completed")
            elif 'LinkedIn' in content or 'post' in content.lower():
                recent_context.append("Previous step: Content writing completed")
    
    if recent_context:
        return "Context: " + "; ".join(recent_context) + ". Continue with next logical step."
    return None

@web_app.route('/')
@optional_auth
def index():
    user = get_current_user()
    # Allow both authenticated and non-authenticated users to access the main app
    return render_template('modern_chat.html', current_user=user)

@web_app.route('/original')
def original_interface():
    return render_template('index.html')

@web_app.route('/chat')
def chat_interface():
    return render_template('chat.html')

@web_app.route('/modern')
def modern_interface():
    return render_template('modern_chat.html')

@web_app.route('/api/chat', methods=['POST'])
@optional_auth
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '')
        history = data.get('history', [])
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Create or use existing thread ID - MOBILE FIX: Handle None thread_id
        thread_id = data.get('thread_id')
        if not thread_id or thread_id == 'None' or thread_id == '':
            thread_id = str(uuid.uuid4())
        print(f"MOBILE FIX: Using thread_id = {thread_id}")
        print(f"CHAT_DEBUG: Received thread_id from frontend = '{data.get('thread_id')}'", flush=True)
        print(f"CHAT_DEBUG: Final thread_id = '{thread_id}'", flush=True)
        
        # CRITICAL FIX: If this is a new conversation (no history), clear any old image context
        # BUT: Don't clear if this is the same thread continuing a conversation
        if (not history or len(history) == 0) and thread_id not in thread_image_context:
            clear_thread_context(thread_id)
            # Also clear web_app level context
            if thread_id in thread_image_context:
                del thread_image_context[thread_id]
            # ADDITIONAL FIX: Reset the global current thread ID to prevent cross-conversation contamination
            reset_all_context()
            print(f"NEW CONVERSATION FIX: Cleared all global context for fresh start")
        else:
            print(f"CONTINUING CONVERSATION: Keeping thread {thread_id} context intact")
        
        # ENHANCED FIX: Also clear context when starting multi-step tasks to prevent contamination
        # BUT: Don't clear if we already have images in context (continuing a workflow)
        is_multi_step_start = any(keyword in message.lower() for keyword in ['create', 'combine', 'generate', 'make']) and len(message.split('.')) >= 2
        has_existing_images = thread_id in thread_image_context and thread_image_context[thread_id]
        if is_multi_step_start and len(history) <= 1 and not has_existing_images:
            clear_thread_context(thread_id)
            reset_all_context()
            print(f"MULTI-STEP START FIX: Cleared context for clean multi-step execution")
        elif is_multi_step_start and has_existing_images:
            print(f"MULTI-STEP CONTINUATION: Keeping existing images in context")
        
        # DEBUG: Log what history is being sent
        print(f"DEBUG HISTORY: thread_id={thread_id}, history_length={len(history) if history else 0}")
        if history:
            print(f"DEBUG HISTORY: first_msg={history[0] if len(history) > 0 else 'none'}")
            print(f"DEBUG HISTORY: last_msg={history[-1] if len(history) > 0 else 'none'}")
        
        # Check if this is a multi-step request and which step we're on
        is_multi_step = detect_multi_step_request(message, history)
        current_step = determine_current_step(message, history)
        
        # ═══════════════════════════════════════════════════════════════════
        # LANGGRAPH-NATIVE CONTEXT MANAGEMENT
        # OLD KEYWORD-BASED INJECTION REMOVED - AI now calls check_available_assets tool
        # ═══════════════════════════════════════════════════════════════════
        #
        # The old code here tried to inject context by detecting keywords like
        # 'convert', 'edit', 'resize', etc. and calling set_recent_image_path().
        #
        # This was:
        # - Brittle (needed hundreds of keywords for all synonyms)
        # - Conflicted with the new LangGraph tool approach
        # - Prevented AI from calling check_available_assets
        #
        # NOW: The AI intelligently calls check_available_assets() when needed
        # and gets file paths from there. No hard-coded keywords required!
        #
        # ═══════════════════════════════════════════════════════════════════
        
        # Build messages list with history
        messages = []
        
        # Add conversation history with enhanced context
        # AGGRESSIVE FIX: If this seems like a fresh conversation, limit history severely
        history_limit = 8
        if len(history) <= 4:  # If very short history, might be new conversation with residual context
            history_limit = 2  # Only keep last 2 messages to prevent context bleeding
        
        for msg in history[-history_limit:]:
            # Add image context information if present, but exclude image content to prevent bleeding
            content = msg.get('content', '')
            
            # CRITICAL FIX: Filter out any HTML img tags from history to prevent image bleeding
            import re
            content = re.sub(r'<img[^>]*>', '', content)
            
            if msg.get('hasImage', False):
                content = f"[Previous message included an image] {content}"
            
            messages.append({
                "role": msg.get('role', 'user'),
                "content": content
            })
        
        # Check for document upload (single or multiple)
        documents = data.get('documents')  # Array for multiple documents
        document_count = data.get('document_count', 0)
        document_path = data.get('document_path')  # Single document (backward compat)
        document_filename = data.get('document_filename')
        document_type = data.get('document_type')

        # Also check history for recent document uploads
        # NOTE: documentData now only contains metadata {name, size, type}, not file paths
        # Files are accessed via unified context in app.py using thread_id
        if not documents and not document_path:
            for msg in reversed(history):
                if msg.get('hasDocument') and msg.get('documentData'):
                    doc_data = msg.get('documentData')
                    if isinstance(doc_data, list):
                        # Multiple documents from history - just track count, files in unified context
                        document_count = len(doc_data)
                        print(f"Found {document_count} document(s) in history (files in unified context)")
                    else:
                        # Single document from history - metadata only
                        # Note: file_path no longer in doc_data, files accessed via unified context
                        print(f"Found document in history: {doc_data.get('name', 'unknown')}")
                    break

        # Add current message with context for document processing
        if documents and document_count > 0:
            # Multiple documents - use metadata for display only
            # Actual file paths come from unified context via check_available_assets tool
            doc_names = [doc.get('name', 'unknown') for doc in documents]
            file_list = '\n'.join([f"  - {name}" for name in doc_names])

            # Check if user wants to combine/merge
            merge_keywords = ['combine', 'merge', 'single pdf', 'into pdf', 'one pdf', 'join']
            wants_merge = any(keyword in message.lower() for keyword in merge_keywords)

            if wants_merge:
                # Explicit instruction to use convert_and_merge_documents
                # Note: AI will get file paths from unified context using check_available_assets
                enhanced_message = f"{message}\n\n[DOCUMENT CONTEXT: User has uploaded {document_count} documents and wants to COMBINE/MERGE them:]\n{file_list}\n\n[INSTRUCTION: Use check_available_assets tool to get file paths, then call convert_and_merge_documents]\n\nDO NOT make up links - call the tools and use their returned HTML links exactly."
            else:
                enhanced_message = f"{message}\n\n[DOCUMENT CONTEXT: User has uploaded {document_count} documents:]\n{file_list}\n\n[INSTRUCTION: Use check_available_assets tool to get file paths if needed for document operations]"
            messages.append({"role": "user", "content": enhanced_message})
        elif document_path and document_filename:
            # Single document processing request
            enhanced_message = f"{message}\n\n[DOCUMENT CONTEXT: User has uploaded a {document_type.upper()} document: {document_filename}]\n[FILE PATH: {document_path}]\n\nPlease use the appropriate conversion tool with this exact file path."
            messages.append({"role": "user", "content": enhanced_message})
        # NOTE: Old keyword-based image context injection removed (lines 349-355)
        # Now handled by AI calling check_available_assets tool in app.py
        else:
            # Check if user is requesting document operation without specifying file
            # Include both phrases ("convert to pdf") and single format names ("pdf", "html")
            conversion_keywords = ['convert', 'to pdf', 'to xlsx', 'to docx', 'to csv', 'to txt', 'to html']
            single_format_keywords = ['pdf', 'xlsx', 'xls', 'docx', 'doc', 'csv', 'txt', 'html', 'pptx', 'ppt']
            manipulation_keywords = ['rotate', 'split', 'compress', 'extract', 'merge', 'degree', 'pages']

            # Check if message is ONLY a format name (like "HTML") - single word requests
            message_stripped = message.strip().lower()
            is_single_format_request = message_stripped in single_format_keywords

            is_conversion = any(keyword in message.lower() for keyword in conversion_keywords) or is_single_format_request
            is_manipulation = any(keyword in message.lower() for keyword in manipulation_keywords)
            has_document_context = thread_id in thread_document_context

            if (is_conversion or is_manipulation) and has_document_context and not documents and not document_path:
                # User wants to perform operation on previously processed document
                doc_context = thread_document_context[thread_id]

                # SMART CONTEXT SELECTION:
                # - Conversions (CSV->PDF, CSV->XLSX) use ORIGINAL uploaded file
                # - Manipulations (rotate, split) use LATEST processed file
                if is_conversion and 'original' in doc_context:
                    selected_doc = doc_context['original']
                    context_type = "original uploaded"
                else:
                    selected_doc = doc_context.get('latest', doc_context.get('original'))
                    context_type = "latest processed"

                doc_file_path = selected_doc['path']
                doc_filename = selected_doc['filename']

                # Extract file extension to help AI select correct conversion tool
                file_ext = doc_filename.rsplit('.', 1)[-1].upper() if '.' in doc_filename else 'UNKNOWN'

                # Check if context is recent (within last 10 minutes to avoid stale context)
                context_age = time.time() - selected_doc.get('timestamp', 0)
                if context_age < 600:  # 10 minutes
                    # CRITICAL: Add system message to override conversation history
                    # The AI might see previous conversions in history (e.g., "CSV was converted to Excel")
                    # This system message ensures the AI uses the correct SOURCE file
                    if is_conversion and context_type == "original uploaded":
                        messages.append({"role": "system", "content": f"CRITICAL CONTEXT OVERRIDE: Ignore any file format references from conversation history. The user is requesting a conversion FROM the ORIGINAL {file_ext} file that was initially uploaded. Even if you see references to converted files (PDF, Excel, etc.) in the chat history, you MUST use the ORIGINAL {file_ext} file located at {doc_file_path} for this conversion request."})

                    enhanced_message = f"{message}\n\n[DOCUMENT CONTEXT: User is referring to the {context_type} {file_ext} file: {doc_filename}]\n[SOURCE FILE TYPE: {file_ext}]\n[FILE PATH: {doc_file_path}]\n\n🚨 CRITICAL: Select the conversion tool based on SOURCE FILE TYPE={file_ext}, NOT any converted files from chat history."
                    messages.append({"role": "user", "content": enhanced_message})
                    print(f"DOCUMENT CONTEXT: Providing {context_type} {file_ext} for {('conversion' if is_conversion else 'manipulation')}: {doc_filename}", file=sys.stderr)
                else:
                    # Context too old, ask user to re-upload
                    messages.append({"role": "user", "content": message})
                    print(f"DOCUMENT CONTEXT: Context too old ({context_age:.0f}s), not using", file=sys.stderr)
            else:
                messages.append({"role": "user", "content": message})
        
        # Add context about multi-step progress to the message
        if is_multi_step and current_step > 1:
            context_msg = get_step_context(history)
            if context_msg:
                messages.append({"role": "system", "content": context_msg})
        
        # Set the current thread ID for tools to access
        set_current_thread_id(thread_id)
        
        # Invoke the LangGraph app with recursion limit
        result = langgraph_app.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
        )
        
        response_content = result["messages"][-1].content

        # CRITICAL FIX: Inject HTML from tool outputs if AI didn't include them
        # This ensures images/videos/links always appear even if GPT-4o paraphrases
        from langchain_core.messages import ToolMessage
        tool_html_outputs = []
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                tool_content = msg.content
                # Check if tool output contains HTML tags
                if tool_content and ('<img src=' in tool_content or '<video' in tool_content or '<a href=' in tool_content):
                    # Extract just the HTML tags, not the descriptive text
                    import re
                    # Find all <img> tags
                    img_tags = re.findall(r'<img[^>]+>', tool_content, re.IGNORECASE)
                    # Find all <video> tags with their content
                    video_tags = re.findall(r'<video[^>]*>.*?</video>', tool_content, re.IGNORECASE | re.DOTALL)
                    # Find all <a> tags
                    link_tags = re.findall(r'<a[^>]+>[^<]*</a>', tool_content, re.IGNORECASE)

                    tool_html_outputs.extend(img_tags)
                    tool_html_outputs.extend(video_tags)
                    tool_html_outputs.extend(link_tags)

        # If we found HTML in tool outputs but it's not in the response, prepend it
        if tool_html_outputs:
            html_content = ' '.join(tool_html_outputs)
            # Check if response already contains this HTML
            if not any(html_tag in response_content for html_tag in tool_html_outputs[:3]):  # Check first 3 tags
                print(f"HTML INJECTION FIX: Adding {len(tool_html_outputs)} HTML elements from tool outputs", file=sys.stderr)
                # Prepend HTML before the conversational response
                response_content = html_content + '\n\n' + response_content

        # CRITICAL FIX: Repair broken download links caused by AI converting HTML to markdown
        # Pattern: "📄 Part 1: Pages 1-3[]()" or "📄 filename.pdf[]()"
        import re
        import glob

        broken_link_pattern = r'([📄📊])\s*([^[\]]+?)\[\]\(\)_?'
        broken_links = list(re.finditer(broken_link_pattern, response_content))

        if broken_links:
            print(f"LINK FIX: Found {len(broken_links)} broken download links, attempting repair...", file=sys.stderr)

            # Get list of files in documents directory to match against
            docs_files = glob.glob(os.path.join(DOCUMENTS_DIR, '*'))
            docs_filenames = {os.path.basename(f): f for f in docs_files}

            for match in broken_links:
                emoji = match.group(1)
                label = match.group(2).strip()
                matched_file = None

                print(f"LINK FIX: Processing broken link with label: '{label}'", file=sys.stderr)

                # Strategy 1: If label contains actual filename with extension, use it directly
                if re.search(r'\.(pdf|docx?|xlsx?|pptx?|png|jpe?g|gif|txt|csv|html?)$', label, re.IGNORECASE):
                    filename = label
                    if filename in docs_filenames:
                        matched_file = filename
                        print(f"LINK FIX: Matched by exact filename: {matched_file}", file=sys.stderr)

                # Strategy 2: For "Part X: Pages Y-Z" pattern, search for matching file
                if not matched_file:
                    part_match = re.search(r'Part (\d+).*Pages (\d+)-(\d+)', label)
                    if part_match:
                        part_num, start_page, end_page = part_match.groups()
                        # Search for file matching pattern
                        pattern = f"*part{part_num}_pages{start_page}-{end_page}.pdf"
                        matching_files = [f for f in docs_filenames.keys() if re.search(rf'part{part_num}_pages{start_page}-{end_page}\.pdf', f, re.IGNORECASE)]
                        if matching_files:
                            matched_file = matching_files[0]
                            print(f"LINK FIX: Matched by part/pages pattern: {matched_file}", file=sys.stderr)

                # Strategy 3: For "Page X" pattern (single page)
                if not matched_file:
                    page_match = re.search(r'Page (\d+)$', label)
                    if page_match:
                        page_num = page_match.group(1)
                        matching_files = [f for f in docs_filenames.keys() if f'_page{page_num}.' in f or f'_page_{page_num}.' in f]
                        if matching_files:
                            matched_file = matching_files[0]
                            print(f"LINK FIX: Matched by page pattern: {matched_file}", file=sys.stderr)

                # If we found a match, replace the broken markdown with proper HTML
                if matched_file:
                    html_link = f'<a href="/documents/{matched_file}" download class="download-link">{emoji} {label}</a>'
                    response_content = response_content.replace(match.group(0), html_link)
                    print(f"LINK FIX: Replaced '{match.group(0)}' with '{html_link}'", file=sys.stderr)
                else:
                    print(f"LINK FIX: WARNING - Could not find matching file for: {label}", file=sys.stderr)

        # DOCUMENT CONTEXT TRACKING: Extract document paths from successful operations
        # This allows follow-up operations like "rotate 180 degrees" without re-specifying the file
        import re
        doc_link_match = re.search(r'<a href="/documents/([^"]+)"', response_content)
        if doc_link_match:
            filename = doc_link_match.group(1)
            document_path = os.path.join(DOCUMENTS_DIR, filename)
            if os.path.exists(document_path):
                # Update only the 'latest' field, preserving 'original'
                if thread_id in thread_document_context:
                    # Preserve original, update latest
                    thread_document_context[thread_id]['latest'] = {
                        'path': document_path,
                        'filename': filename,
                        'timestamp': time.time()
                    }
                    print(f"DOCUMENT CONTEXT: Updated 'latest' for thread {thread_id}: {filename}", file=sys.stderr)

                    # ALSO update context in app.py for LangGraph check_available_assets tool
                    update_document_latest(thread_id, document_path, filename)
                else:
                    # First operation (shouldn't happen if upload initialized context)
                    thread_document_context[thread_id] = {
                        'original': {
                            'path': document_path,
                            'filename': filename,
                            'timestamp': time.time()
                        },
                        'latest': {
                            'path': document_path,
                            'filename': filename,
                            'timestamp': time.time()
                        }
                    }
                    print(f"DOCUMENT CONTEXT: Initialized thread {thread_id} with document: {filename}", file=sys.stderr)
            else:
                print(f"DOCUMENT CONTEXT: File not found: {document_path}", file=sys.stderr)

        # DEBUG: Log the actual response content to see what we're working with
        print(f"DEBUG RESPONSE: {response_content}", file=sys.stderr)
        print(f"DEBUG: Looking for 'Image saved to' pattern", file=sys.stderr)
        
        # ROBUST FIX: Extract image path from HTML src attribute instead of relying on text
        import re
        img_match = re.search(r'<img[^>]*src="/assets/([^"]+)"', response_content)
        if img_match:
            filename = img_match.group(1)
            # FIXED: Use full absolute path for Railway persistent storage
            generated_image_path = os.path.join(ASSETS_DIR, filename)
            thread_image_context[thread_id] = generated_image_path
            print(f"ROBUST FIX: Updated thread {thread_id} context with generated image: {generated_image_path}", file=sys.stderr)
            
            # CRITICAL FIX: Also sync with app.py's thread context for editing
            set_recent_image_path(generated_image_path, thread_id)
            print(f"ROBUST FIX: Updated app.py thread context for {thread_id}: {generated_image_path}", file=sys.stderr)
        
        # LEGACY: Keep the old text-based parsing as fallback
        elif 'Image saved to' in response_content:
            # Extract the image path from the response
            import re
            path_match = re.search(r'Image saved to (.*?)(?:\s|$)', response_content)
            if path_match:
                raw_path = path_match.group(1).strip()
                # FIXED: Ensure absolute path for Railway persistent storage
                if not os.path.isabs(raw_path):
                    # If it's a relative path like 'assets/filename', make it absolute
                    if raw_path.startswith('assets/'):
                        generated_image_path = os.path.join(ASSETS_DIR, raw_path[7:])  # Remove 'assets/' prefix
                    else:
                        generated_image_path = os.path.join(ASSETS_DIR, raw_path)
                else:
                    generated_image_path = raw_path
                    
                thread_image_context[thread_id] = generated_image_path
                print(f"LEGACY: Updated thread {thread_id} context with generated image: {generated_image_path}", file=sys.stderr)
                
                # CRITICAL FIX: Also sync with app.py's thread context for editing
                set_recent_image_path(generated_image_path, thread_id)
                print(f"LEGACY: Updated app.py thread context for {thread_id}: {generated_image_path}", file=sys.stderr)
        
        # ADDITIONAL FIX: Also handle edited images
        if 'Image edit completed:' in response_content:
            import re
            path_match = re.search(r'Saved as (.*?)(?:\s|$)', response_content)
            if path_match:
                raw_path = path_match.group(1).strip()
                # FIXED: Ensure absolute path for Railway persistent storage
                if not os.path.isabs(raw_path):
                    # If it's a relative path like 'assets/filename', make it absolute
                    if raw_path.startswith('assets/'):
                        edited_image_path = os.path.join(ASSETS_DIR, raw_path[7:])  # Remove 'assets/' prefix
                    else:
                        edited_image_path = os.path.join(ASSETS_DIR, raw_path)
                else:
                    edited_image_path = raw_path
                
                thread_image_context[thread_id] = edited_image_path
                print(f"Updated thread {thread_id} context with edited image: {edited_image_path}")
                
                # Sync with app.py's thread context for future operations
                set_recent_image_path(edited_image_path, thread_id)
                print(f"EDIT SYNC FIX: Updated app.py thread context for {thread_id}: {edited_image_path}")
        
        # DISABLED PROBLEMATIC FALLBACK: This was causing inappropriate image attachments
        # The agent should handle image operations correctly without fallback
        pass
        
        return jsonify({
            'response': response_content,
            'thread_id': thread_id
        })

    except Exception as e:
        # Log full traceback for debugging
        import traceback
        print(f"ERROR in /api/chat: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/analyze-image', methods=['POST'])
@optional_auth
def analyze_image():
    try:
        # Handle both single and multiple image uploads automatically
        uploaded_files = []
        
        # Check for single image upload (legacy support)
        if 'image' in request.files:
            single_file = request.files['image']
            if single_file.filename != '':
                uploaded_files = [single_file]
        
        # Check for multiple image upload
        if 'images' in request.files:
            multi_files = request.files.getlist('images')
            uploaded_files = [f for f in multi_files if f.filename != '']
        
        if not uploaded_files:
            return jsonify({'error': 'No image files provided'}), 400
        
        # Default messages based on image count
        if len(uploaded_files) == 1:
            default_message = 'What\'s in this image?'
        else:
            default_message = f'Combine these {len(uploaded_files)} images into one artistic composition'
            
        message = request.form.get('message', default_message)
        
        # Validate file types and count
        for i, file in enumerate(uploaded_files):
            if not allowed_file(file.filename):
                return jsonify({'error': f'Invalid file type in image {i+1}. Allowed: png, jpg, jpeg, gif, webp'}), 400

        if len(uploaded_files) > 100:
            return jsonify({'error': 'Maximum 100 images allowed'}), 400
        
        # Save all uploaded files
        saved_paths = []
        timestamp = int(time.time())
        
        for i, file in enumerate(uploaded_files):
            filename = secure_filename(file.filename)
            unique_filename = f"{timestamp}_{i}_{filename}"
            file_path = os.path.join(web_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            saved_paths.append(file_path)
        
        thread_id = str(uuid.uuid4())
        
        if len(uploaded_files) == 1:
            # Single image - traditional analysis/editing workflow with vision
            file_path = saved_paths[0]
            filename = uploaded_files[0].filename

            # Determine MIME type
            file_ext = filename.lower().split('.')[-1]
            mime_type = {
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'webp': 'image/webp'
            }.get(file_ext, 'image/jpeg')

            # Store image path in context - AI agent will access via tools
            recent_images[thread_id] = file_path
            thread_image_context[thread_id] = file_path
            set_recent_image_path(file_path, thread_id)
            print(f"AGENT: Stored image {filename} in context for thread {thread_id}")

            # ═══════════════════════════════════════════════════════════════
            # AGENT-DRIVEN ARCHITECTURE - NO HARDCODED KEYWORDS
            # ═══════════════════════════════════════════════════════════════
            # Backend is now a "dumb pipe" - just stores file and sends message
            # AI agent decides what to do based on user intent:
            #
            # - "analyze this image" → AI calls vision analysis tool
            # - "create a link" → AI calls create_shareable_link tool
            # - "edit to make it darker" → AI calls edit_image tool
            # - "animate this" → AI calls generate_video_from_image tool
            #
            # Maximum flexibility - AI handles ALL intent detection
            # ═══════════════════════════════════════════════════════════════

            user_msg = {
                "role": "user",
                "content": f"{message}\n\n[File uploaded: {filename}]",
            }
            print(f"AGENT: Sending text-only message, AI will decide what tools to use")
        else:
            # Multiple images - set up thread-specific context for multi-image fusion
            from app import get_thread_context
            context = get_thread_context(thread_id)
            # Clear old images for this thread and add new ones
            context['uploaded_images'] = [os.path.abspath(path) for path in saved_paths]
            # Set the most recent image as the recent path
            if saved_paths:
                context['recent_path'] = os.path.abspath(saved_paths[-1])
            
            print(f"DEBUG: Multi-image upload - thread {thread_id}", flush=True)
            print(f"DEBUG: saved_paths = {saved_paths}", flush=True)
            print(f"DEBUG: context uploaded_images = {context['uploaded_images']}", flush=True)
            print(f"DEBUG: context recent_path = {context['recent_path']}", flush=True)
            
            user_msg = {
                "role": "user",
                "content": f"{message} [Multi-image request with {len(saved_paths)} uploaded images]"
            }
        
        # Set the current thread ID for tools to access
        set_current_thread_id(thread_id)
        
        # Invoke the LangGraph app - agent will decide what to do based on prompt and image count
        result = langgraph_app.invoke(
            {"messages": [user_msg]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
        )
        
        response_content = result["messages"][-1].content

        # CRITICAL FIX: Inject HTML from tool outputs if AI didn't include them
        # This ensures images/videos/links always appear even if GPT-4o paraphrases
        from langchain_core.messages import ToolMessage
        tool_html_outputs = []
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage):
                tool_content = msg.content
                # Check if tool output contains HTML tags
                if tool_content and ('<img src=' in tool_content or '<video' in tool_content or '<a href=' in tool_content):
                    # Extract just the HTML tags, not the descriptive text
                    import re
                    # Find all <img> tags
                    img_tags = re.findall(r'<img[^>]+>', tool_content, re.IGNORECASE)
                    # Find all <video> tags with their content
                    video_tags = re.findall(r'<video[^>]*>.*?</video>', tool_content, re.IGNORECASE | re.DOTALL)
                    # Find all <a> tags
                    link_tags = re.findall(r'<a[^>]+>[^<]*</a>', tool_content, re.IGNORECASE)

                    tool_html_outputs.extend(img_tags)
                    tool_html_outputs.extend(video_tags)
                    tool_html_outputs.extend(link_tags)

        # If we found HTML in tool outputs but it's not in the response, prepend it
        if tool_html_outputs:
            html_content = ' '.join(tool_html_outputs)
            # Check if response already contains this HTML
            if not any(html_tag in response_content for html_tag in tool_html_outputs[:3]):  # Check first 3 tags
                print(f"HTML INJECTION FIX (analyze-image): Adding {len(tool_html_outputs)} HTML elements from tool outputs", file=sys.stderr)
                # Prepend HTML before the conversational response
                response_content = html_content + '\n\n' + response_content

        # DISABLED PROBLEMATIC FALLBACK: This was causing Krishna image to appear inappropriately
        # The agent should handle image operations correctly without fallback
        pass

        return jsonify({
            'response': response_content,
            'thread_id': thread_id,
            'uploaded_count': len(saved_paths),
            'uploaded_image_path': saved_paths[0] if len(saved_paths) == 1 else None,
            'uploaded_image_paths': saved_paths if len(saved_paths) > 1 else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/assets/<filename>')
def serve_asset(filename):
    return send_from_directory(ASSETS_DIR, filename)

@web_app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(web_app.config['UPLOAD_FOLDER'], filename)

@web_app.route('/logo.png')
def serve_logo():
    return send_from_directory('.', 'logo.png')

@web_app.route('/favicon.png')
def serve_favicon():
    return send_from_directory('.', 'favicon.png')

# Serve IndexNow verification file
@web_app.route('/dc42f34e7a2e52048e3d62723b7193017d5f13cc23ca4322b9ebb5e2e2ada103.txt')
def serve_indexnow_key():
    """Serve IndexNow API key verification file for instant search engine indexing"""
    return send_from_directory('.', 'dc42f34e7a2e52048e3d62723b7193017d5f13cc23ca4322b9ebb5e2e2ada103.txt')

@web_app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEOS_DIR, filename)

# === UNIFIED FILE UPLOAD (Agent-Driven - No Hardcoded Logic) ================

@web_app.route('/api/upload-file', methods=['POST'])
@optional_auth
def upload_file_unified():
    """
    UNIFIED file upload endpoint - accepts ANY file type (images, PDFs, videos, etc.)
    Frontend is a "dumb pipe" - just uploads the file
    AI agent decides what to do based on user's message

    NO hardcoded logic for file types or operations
    Maximum flexibility for agentic applications
    """
    try:
        thread_id = request.form.get('thread_id', 'default')
        message = request.form.get('message', '')
        file = request.files.get('file')

        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        # Save file to uploads directory
        filename = secure_filename(file.filename)
        timestamp = int(time.time() * 1000)
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(web_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        file_size = os.path.getsize(file_path)

        # DEBUG: Log thread_id before adding to context
        print(f"UNIFIED_UPLOAD_BACKEND: Received thread_id = '{thread_id}'", flush=True)
        print(f"UNIFIED_UPLOAD_BACKEND: Filename = '{filename}'", flush=True)
        print(f"UNIFIED_UPLOAD_BACKEND: File path = '{file_path}'", flush=True)

        # Add to unified context - NO decisions about what to do with it
        file_info = add_uploaded_file(
            thread_id=thread_id,
            file_path=file_path,
            filename=filename,
            file_size=file_size
        )

        print(f"UNIFIED_UPLOAD: Stored '{filename}' in context for thread {thread_id}")
        print(f"UNIFIED_UPLOAD: File added as category: {file_info['category']}", flush=True)
        print(f"UNIFIED_UPLOAD: AI agent will decide what to do based on user message: '{message}'")

        # Return success - AI agent will access file from context
        return jsonify({
            'success': True,
            'filename': filename,
            'size': file_size,
            'message': f'File uploaded: {filename}'
        })

    except Exception as e:
        print(f"ERROR in unified upload: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# === DOCUMENT PROCESSING ENDPOINTS ==========================================

@web_app.route('/documents/<filename>')
def serve_document(filename):
    """Serve converted document files"""
    return send_from_directory(DOCUMENTS_DIR, filename)

@web_app.route('/api/upload-document', methods=['POST'])
@optional_auth
def upload_document():
    """
    Upload a document (PDF, Word, Excel, PowerPoint) for processing.
    The AI can then convert it to other formats or analyze it.
    """
    try:
        if 'document' not in request.files:
            return jsonify({'error': 'No document file provided'}), 400

        file = request.files['document']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file has extension (all file types accepted)
        if not allowed_document(file.filename):
            return jsonify({
                'error': 'Invalid file: file must have an extension'
            }), 400

        # Save the uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"

        # Save to documents directory for permanent storage
        file_path = os.path.join(DOCUMENTS_DIR, unique_filename)
        file.save(file_path)

        # Get file info
        file_size = os.path.getsize(file_path)
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Generate thread ID for this document session
        thread_id = str(uuid.uuid4())

        # DOCUMENT CONTEXT TRACKING: Store original uploaded file
        # This will never be overwritten, allowing multiple conversions from same source
        thread_document_context[thread_id] = {
            'original': {
                'path': file_path,
                'filename': unique_filename,
                'timestamp': timestamp
            },
            'latest': {
                'path': file_path,
                'filename': unique_filename,
                'timestamp': timestamp
            }
        }
        print(f"DOCUMENT CONTEXT: Initialized thread {thread_id} with original: {unique_filename}", file=sys.stderr)

        # ALSO set context in app.py for LangGraph check_available_assets tool
        set_document_context(thread_id, file_path, unique_filename, is_original=True)

        # Prepare response with file information
        response_data = {
            'success': True,
            'file_path': file_path,
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': file_size,
            'file_type': file_ext,
            'thread_id': thread_id,
            'message': f'✅ Uploaded {filename} ({file_size // 1024}KB). You can now ask me to convert or analyze it!'
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/upload-documents', methods=['POST'])
@optional_auth
def upload_documents():
    """
    Upload multiple documents (up to 100) for batch processing.
    Supports PDF, Word, Excel, PowerPoint files, and images for PDF conversion.
    """
    try:
        # Get the count of documents
        count = int(request.form.get('count', 0))

        if count == 0 or count > 100:
            return jsonify({'error': 'Please upload 1-100 documents'}), 400

        uploaded_docs = []

        # Process each document
        for i in range(count):
            file_key = f'document{i}'
            if file_key not in request.files:
                continue

            file = request.files[file_key]

            if file.filename == '':
                continue

            # Validate file has extension (all file types accepted)
            if not allowed_document(file.filename):
                return jsonify({
                    'error': f'Invalid file: {file.filename} must have an extension'
                }), 400

            # Save the uploaded file
            filename = secure_filename(file.filename)
            timestamp = int(time.time())
            unique_filename = f"{timestamp}_{i}_{filename}"

            # Save to documents directory
            file_path = os.path.join(DOCUMENTS_DIR, unique_filename)
            file.save(file_path)

            # Get file info
            file_size = os.path.getsize(file_path)
            file_ext = filename.rsplit('.', 1)[1].lower()

            uploaded_docs.append({
                'file_path': file_path,
                'filename': unique_filename,
                'original_filename': filename,
                'file_size': file_size,
                'file_type': file_ext
            })

        if len(uploaded_docs) == 0:
            return jsonify({'error': 'No valid documents uploaded'}), 400

        # Generate thread ID for this batch
        thread_id = str(uuid.uuid4())

        # Prepare response
        total_size = sum(doc['file_size'] for doc in uploaded_docs)
        filenames = ', '.join(doc['original_filename'] for doc in uploaded_docs)

        response_data = {
            'success': True,
            'documents': uploaded_docs,
            'count': len(uploaded_docs),
            'thread_id': thread_id,
            'message': f'✅ Uploaded {len(uploaded_docs)} document(s) ({total_size // 1024}KB total): {filenames}. You can now ask me to convert or analyze them!'
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === PERMANENT FILE LINKS ENDPOINT ==========================================

@web_app.route('/api/upload-permanent', methods=['POST'])
@optional_auth
def upload_permanent_file():
    """
    Upload a file and get a permanent shareable link.
    Returns a short URL like https://aiezzy.com/f5h39dhekl79e.gif
    Supports all file types (images, videos, documents, etc.)
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save the uploaded file with secure filename
        original_filename = secure_filename(file.filename)
        file_extension = ''
        if '.' in original_filename:
            file_extension = original_filename.rsplit('.', 1)[1].lower()

        # Generate unique short ID
        short_id = generate_short_id(12)

        # Create filename with short ID and extension
        if file_extension:
            stored_filename = f"{short_id}.{file_extension}"
        else:
            stored_filename = short_id

        # Save file to permanent storage
        file_path = os.path.join(PERMANENT_FILES_DIR, stored_filename)
        file.save(file_path)

        # Get file info
        file_size = os.path.getsize(file_path)
        timestamp = int(time.time())

        # Get user ID if authenticated
        user_id = get_user_id()

        # Save to database
        db = load_permanent_files_db()
        db[short_id] = {
            'filename': stored_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size,
            'file_extension': file_extension,
            'timestamp': timestamp,
            'user_id': user_id,
            'views': 0
        }
        save_permanent_files_db(db)

        # Generate permanent link
        base_url = request.host_url.rstrip('/')
        permanent_link = f"{base_url}/{short_id}"
        if file_extension:
            permanent_link += f".{file_extension}"

        response_data = {
            'success': True,
            'short_id': short_id,
            'permanent_link': permanent_link,
            'filename': stored_filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'file_type': file_extension,
            'message': f'✅ File uploaded successfully! Permanent link: {permanent_link}'
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================

@web_app.route('/api/clear-context', methods=['POST'])
def clear_context():
    """Clear image context for a thread - useful when starting new conversations"""
    try:
        data = request.get_json()
        thread_id = data.get('thread_id')
        
        if thread_id:
            clear_thread_context(thread_id)
            if thread_id in thread_image_context:
                del thread_image_context[thread_id]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/reset-all-context', methods=['POST'])
def reset_context():
    """Reset all image context - for debugging"""
    try:
        reset_all_context()
        global thread_image_context
        thread_image_context.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Removed analyze-multi-images endpoint - now handled by unified analyze-image endpoint

# Authentication Endpoints
@web_app.route('/login')
def login_page():
    """Login page"""
    return render_template('auth/login.html')

@web_app.route('/register')
def register_page():
    """Registration page"""
    return render_template('auth/register.html')

@web_app.route('/profile')
@login_required
def profile_page():
    """User profile page"""
    user = get_current_user()
    return render_template('auth/profile.html', user=user)

@web_app.route('/api/register', methods=['POST'])
def api_register():
    """User registration API endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Rate limiting removed - allow unlimited registration attempts
        client_ip = get_client_ip()  # Still needed for logging
        
        # Validation
        if not email or not is_valid_email(email):
            return jsonify({'error': 'Valid email is required'}), 400
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Password strength validation (simplified)
        password_errors = validate_password_strength(password)
        if password_errors:
            return jsonify({'error': password_errors[0]}), 400  # Return first error
        
        # Create user (username will be auto-generated from email)
        result = user_manager.create_user(email, password)
        
        if result['success']:
            # Log account creation activity
            user_manager.log_activity(
                result['user_id'], 
                'account_created', 
                {'username': result['username'], 'email': email},
                client_ip
            )
            
            # Auto-login the newly registered user
            # Authenticate the user to get session token
            login_result = user_manager.authenticate_user(
                result['username'], password, client_ip, get_user_agent()
            )
            
            if login_result['success']:
                # Create session for auto-login
                create_session(login_result['user'], login_result['session_token'])
                
                return jsonify({
                    'success': True,
                    'message': 'Account created successfully. You are now logged in.',
                    'user': login_result['user'],
                    'session_token': login_result['session_token']
                })
            else:
                # If auto-login fails for some reason, still return success but without session
                return jsonify({
                    'success': True,
                    'message': 'Account created successfully. Please log in.',
                    'user_id': result['user_id'],
                    'username': result['username']
                })
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/login', methods=['POST'])
def api_login():
    """User login API endpoint"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember_me = data.get('remember_me', False)
        
        # Rate limiting removed - allow unlimited login attempts
        client_ip = get_client_ip()  # Still needed for logging
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Authenticate user
        result = user_manager.authenticate_user(
            username, password, client_ip, get_user_agent()
        )
        
        if result['success']:
            # Create session
            create_session(result['user'], result['session_token'])
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': result['user'],
                'session_token': result['session_token']
            })
        else:
            return jsonify(result), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """User logout API endpoint"""
    try:
        from auth import g
        
        # Get session token
        session_token = getattr(g, 'session_token', None) or session.get('session_token')
        
        if session_token:
            user_manager.logout_user(session_token)
        
        # Clear session
        clear_session()
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/user/profile', methods=['GET'])
@login_required
def api_get_profile():
    """Get user profile"""
    try:
        user = get_current_user()
        user_id = user['id']
        
        # Get user stats
        stats = user_manager.get_user_stats(user_id)
        
        return jsonify({
            'success': True,
            'user': user,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/user/profile', methods=['PUT'])
@login_required
def api_update_profile():
    """Update user profile"""
    try:
        user = get_current_user()
        user_id = user['id']
        data = request.get_json()
        
        # Extract allowed fields
        update_data = {}
        if 'full_name' in data:
            update_data['full_name'] = data['full_name'].strip()
        if 'email' in data:
            email = data['email'].strip().lower()
            if not is_valid_email(email):
                return jsonify({'error': 'Invalid email format'}), 400
            update_data['email'] = email
        
        # Update profile
        result = user_manager.update_user_profile(user_id, **update_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/user/change-password', methods=['PUT'])
@login_required
def api_change_password():
    """Change user password"""
    try:
        user = get_current_user()
        user_id = user['id']
        data = request.get_json()
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return jsonify({'error': 'Both old and new passwords are required'}), 400
        
        # Password strength validation
        password_errors = validate_password_strength(new_password)
        if password_errors:
            return jsonify({'error': password_errors[0]}), 400
        
        # Change password
        result = user_manager.change_password(user_id, old_password, new_password)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/user/check-auth', methods=['GET'])
@optional_auth
def api_check_auth():
    """Check if user is authenticated"""
    user = get_current_user()
    if user:
        return jsonify({
            'authenticated': True,
            'user': user
        })
    else:
        return jsonify({'authenticated': False})

@web_app.route('/api/share-conversation', methods=['POST'])
def share_conversation():
    """Create a public link for sharing a conversation"""
    try:
        data = request.get_json()
        conversation_data = data.get('conversation')
        
        if not conversation_data:
            return jsonify({'error': 'Conversation data is required'}), 400
        
        # Generate a unique share ID
        share_id = secrets.token_urlsafe(16)  # Creates URL-safe random string
        
        # Store the conversation data
        shared_conversation = {
            'id': share_id,
            'title': conversation_data.get('title', 'AIezzy Conversation'),
            'messages': conversation_data.get('messages', []),
            'created_at': time.time(),
            'shared_at': time.time()
        }
        
        # Save to persistent storage
        shared_file_path = os.path.join('shared', f'{share_id}.json')
        with open(shared_file_path, 'w') as f:
            json.dump(shared_conversation, f, indent=2)
        
        # Also store in memory for quick access
        shared_conversations[share_id] = shared_conversation
        
        # Get the base URL (works for both localhost and production)
        base_url = request.host_url.rstrip('/')
        share_url = f"{base_url}/share/{share_id}"
        
        return jsonify({
            'success': True,
            'share_id': share_id,
            'share_url': share_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/share/<share_id>')
def view_shared_conversation(share_id):
    """View a shared conversation"""
    try:
        # Try to load from memory first
        shared_conversation = shared_conversations.get(share_id)
        
        # If not in memory, try to load from file
        if not shared_conversation:
            shared_file_path = os.path.join('shared', f'{share_id}.json')
            if os.path.exists(shared_file_path):
                with open(shared_file_path, 'r') as f:
                    shared_conversation = json.load(f)
                    shared_conversations[share_id] = shared_conversation
        
        if not shared_conversation:
            return render_template('shared_not_found.html'), 404
        
        # Process messages to ensure image paths are properly handled
        processed_messages = []
        for message in shared_conversation['messages']:
            processed_message = message.copy()
            # Ensure content has proper image paths
            if 'content' in processed_message:
                content = processed_message['content']
                # Debug: print the content to see what we're working with
                if '<img' in content or 'assets/' in content:
                    print(f"DEBUG: Processing message content with images: {content[:200]}...")
            processed_messages.append(processed_message)
        
        shared_conversation['messages'] = processed_messages
        
        return render_template('shared_conversation.html', 
                             conversation=shared_conversation, 
                             share_id=share_id)
        
    except Exception as e:
        return render_template('shared_error.html', error=str(e)), 500

@web_app.route('/api/save-conversation', methods=['POST'])
@optional_auth
def save_conversation():
    """Save a conversation to server-side storage for persistence"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        conversation_data = data.get('conversation_data')
        user_id = get_user_id()  # Get authenticated user ID
        
        if not conversation_id or not conversation_data:
            return jsonify({'error': 'Missing conversation_id or conversation_data'}), 400
        
        # Create user-specific conversation directory
        user_conv_dir = os.path.join(CONVERSATIONS_DIR, user_id)
        os.makedirs(user_conv_dir, exist_ok=True)
        
        # Save conversation to file
        conv_file_path = os.path.join(user_conv_dir, f'{conversation_id}.json')
        
        # Add server-side metadata
        enhanced_conversation = {
            **conversation_data,
            'saved_at': time.time(),
            'user_id': user_id,
            'server_saved': True
        }
        
        with open(conv_file_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_conversation, f, indent=2, ensure_ascii=False)
        
        # Also store in memory for quick access
        if user_id not in user_conversations:
            user_conversations[user_id] = {}
        user_conversations[user_id][conversation_id] = enhanced_conversation
        
        return jsonify({
            'success': True, 
            'message': 'Conversation saved successfully',
            'saved_at': enhanced_conversation['saved_at']
        })
        
    except Exception as e:
        print(f"Error saving conversation: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/load-conversations')
@optional_auth
def load_conversations():
    """Load all conversations for a user from server-side storage"""
    try:
        user_id = get_user_id()  # Get authenticated user ID
        
        # Load from memory first
        if user_id in user_conversations:
            conversations = user_conversations[user_id]
        else:
            conversations = {}
            
        # Load from files if not in memory
        user_conv_dir = os.path.join(CONVERSATIONS_DIR, user_id)
        if os.path.exists(user_conv_dir):
            for filename in os.listdir(user_conv_dir):
                if filename.endswith('.json'):
                    conv_id = filename[:-5]  # Remove .json extension
                    if conv_id not in conversations:
                        conv_file_path = os.path.join(user_conv_dir, filename)
                        try:
                            with open(conv_file_path, 'r', encoding='utf-8') as f:
                                conversation = json.load(f)
                                conversations[conv_id] = conversation
                        except Exception as e:
                            print(f"Error loading conversation {filename}: {e}")
            
            # Store in memory for next time
            user_conversations[user_id] = conversations
        
        # Sort conversations by lastUpdated or saved_at
        sorted_conversations = []
        for conv_id, conv_data in conversations.items():
            sorted_conversations.append({
                'id': conv_id,
                'title': conv_data.get('title', 'Untitled Chat'),
                'lastUpdated': conv_data.get('lastUpdated', conv_data.get('saved_at', 0)),
                'messageCount': len(conv_data.get('messages', [])),
                'server_saved': conv_data.get('server_saved', False)
            })
        
        sorted_conversations.sort(key=lambda x: x['lastUpdated'], reverse=True)
        
        return jsonify({
            'success': True,
            'conversations': sorted_conversations[:50]  # Limit to 50 recent conversations
        })
        
    except Exception as e:
        print(f"Error loading conversations: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/get-conversation/<conversation_id>')
@optional_auth
def get_conversation(conversation_id):
    """Get a specific conversation by ID"""
    try:
        user_id = get_user_id()  # Get authenticated user ID
        
        # Check memory first
        if user_id in user_conversations and conversation_id in user_conversations[user_id]:
            conversation = user_conversations[user_id][conversation_id]
        else:
            # Load from file
            conv_file_path = os.path.join(CONVERSATIONS_DIR, user_id, f'{conversation_id}.json')
            if os.path.exists(conv_file_path):
                with open(conv_file_path, 'r', encoding='utf-8') as f:
                    conversation = json.load(f)
                
                # Store in memory
                if user_id not in user_conversations:
                    user_conversations[user_id] = {}
                user_conversations[user_id][conversation_id] = conversation
            else:
                return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({
            'success': True,
            'conversation': conversation
        })
        
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/delete-conversation/<conversation_id>', methods=['DELETE'])
@optional_auth
def delete_conversation(conversation_id):
    """Delete a conversation from server storage"""
    try:
        user_id = get_user_id()  # Get authenticated user ID
        
        # Remove from memory
        if user_id in user_conversations and conversation_id in user_conversations[user_id]:
            del user_conversations[user_id][conversation_id]
        
        # Remove file
        conv_file_path = os.path.join(CONVERSATIONS_DIR, user_id, f'{conversation_id}.json')
        if os.path.exists(conv_file_path):
            os.remove(conv_file_path)
            return jsonify({'success': True, 'message': 'Conversation deleted'})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
            
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/export-conversation/<conversation_id>')
@login_required
def export_conversation(conversation_id):
    """Export a conversation as JSON, Markdown, or HTML"""
    try:
        user_id = get_user_id()  # Get authenticated user ID
        export_format = request.args.get('format', 'json').lower()
        
        # Get conversation data
        conv_file_path = os.path.join(CONVERSATIONS_DIR, user_id, f'{conversation_id}.json')
        if not os.path.exists(conv_file_path):
            return jsonify({'error': 'Conversation not found'}), 404
        
        with open(conv_file_path, 'r', encoding='utf-8') as f:
            conversation = json.load(f)
        
        if export_format == 'json':
            # Return raw JSON
            return jsonify(conversation)
        
        elif export_format == 'markdown':
            # Convert to Markdown format
            markdown_content = f"# {conversation.get('title', 'Conversation')}\n\n"
            markdown_content += f"*Exported on {time.strftime('%B %d, %Y at %I:%M %p')}*\n\n"
            markdown_content += "---\n\n"
            
            for message in conversation.get('messages', []):
                if message.get('isUser'):
                    markdown_content += f"**You:** {message['content']}\n\n"
                else:
                    # Clean up HTML for markdown
                    import re
                    content = message['content']
                    # Convert HTML images to markdown
                    content = re.sub(r'<img[^>]+src="([^"]+)"[^>]*>', r'![Image](\1)', content)
                    # Remove other HTML tags
                    content = re.sub(r'<[^>]+>', '', content)
                    markdown_content += f"**AIezzy:** {content}\n\n"
            
            return markdown_content, 200, {'Content-Type': 'text/markdown'}
        
        elif export_format == 'html':
            # Convert to HTML format
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{conversation.get('title', 'Conversation')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .message {{ margin: 20px 0; padding: 15px; border-radius: 8px; }}
        .user {{ background: #f0f9ff; border-left: 4px solid #0ea5e9; }}
        .assistant {{ background: #f9fafb; border-left: 4px solid #6b7280; }}
        .timestamp {{ color: #6b7280; font-size: 12px; margin-top: 5px; }}
        img {{ max-width: 100%; height: auto; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>{conversation.get('title', 'Conversation')}</h1>
    <p><em>Exported on {time.strftime('%B %d, %Y at %I:%M %p')}</em></p>
    <hr>
"""
            
            for message in conversation.get('messages', []):
                css_class = 'user' if message.get('isUser') else 'assistant'
                sender = 'You' if message.get('isUser') else 'AIezzy'
                
                html_content += f"""
    <div class="message {css_class}">
        <strong>{sender}:</strong>
        <div>{message['content']}</div>
        {f'<div class="timestamp">{message.get("timestamp", "")}</div>' if message.get('timestamp') else ''}
    </div>
"""
            
            html_content += """
</body>
</html>
"""
            return html_content, 200, {'Content-Type': 'text/html'}
        
        else:
            return jsonify({'error': 'Invalid format. Use json, markdown, or html'}), 400
            
    except Exception as e:
        print(f"Error exporting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/export-all-conversations')
@login_required
def export_all_conversations():
    """Export all conversations as a ZIP file"""
    try:
        user_id = get_user_id()  # Get authenticated user ID
        export_format = request.args.get('format', 'json').lower()
        
        import zipfile
        from io import BytesIO
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            user_conv_dir = os.path.join(CONVERSATIONS_DIR, user_id)
            
            if os.path.exists(user_conv_dir):
                for filename in os.listdir(user_conv_dir):
                    if filename.endswith('.json'):
                        conv_id = filename[:-5]  # Remove .json extension
                        
                        # Get conversation in requested format
                        if export_format == 'json':
                            file_path = os.path.join(user_conv_dir, filename)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            zip_file.writestr(f"{conv_id}.json", content)
                        
                        else:
                            # For markdown/html, we need to call the export function
                            with open(os.path.join(user_conv_dir, filename), 'r', encoding='utf-8') as f:
                                conversation = json.load(f)
                            
                            title = conversation.get('title', 'Conversation').replace('/', '_')
                            safe_filename = f"{title}_{conv_id}"
                            
                            if export_format == 'markdown':
                                # Generate markdown content
                                markdown_content = f"# {conversation.get('title', 'Conversation')}\n\n"
                                for message in conversation.get('messages', []):
                                    if message.get('isUser'):
                                        markdown_content += f"**You:** {message['content']}\n\n"
                                    else:
                                        import re
                                        content = message['content']
                                        content = re.sub(r'<img[^>]+src="([^"]+)"[^>]*>', r'![Image](\1)', content)
                                        content = re.sub(r'<[^>]+>', '', content)
                                        markdown_content += f"**AIezzy:** {content}\n\n"
                                
                                zip_file.writestr(f"{safe_filename}.md", markdown_content)
        
        zip_buffer.seek(0)
        
        from flask import send_file
        return send_file(
            BytesIO(zip_buffer.read()),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'aiezzy_conversations_{user_id}_{int(time.time())}.zip'
        )
        
    except Exception as e:
        print(f"Error exporting all conversations: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/shared-conversations')
def list_shared_conversations():
    """List all shared conversations (for management)"""
    try:
        # Load all shared conversations from files
        shared_dir = 'shared'
        conversations = []
        
        if os.path.exists(shared_dir):
            for filename in os.listdir(shared_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(shared_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            conv = json.load(f)
                            conversations.append({
                                'id': conv['id'],
                                'title': conv['title'],
                                'shared_at': conv['shared_at'],
                                'message_count': len(conv['messages'])
                            })
                    except:
                        continue
        
        # Sort by shared_at descending
        conversations.sort(key=lambda x: x['shared_at'], reverse=True)
        
        return jsonify({'conversations': conversations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/feature-request', methods=['POST'])
def submit_feature_request():
    """Submit a new feature request"""
    try:
        data = request.get_json()
        feature_name = data.get('featureName', '').strip()
        feature_details = data.get('featureDetails', '').strip()
        requested_by = data.get('requestedBy', 'Anonymous').strip()
        
        if not feature_name or not feature_details:
            return jsonify({'error': 'Feature name and details are required'}), 400
        
        # Generate a unique request ID
        request_id = secrets.token_urlsafe(12)
        
        # Create feature request object
        feature_request = {
            'id': request_id,
            'feature_name': feature_name,
            'feature_details': feature_details,
            'requested_by': requested_by,
            'votes': 0,
            'voters': [],
            'status': 'open',  # open, in_progress, completed, rejected
            'created_at': time.time(),
            'updated_at': time.time()
        }
        
        # Save to persistent storage
        feature_file_path = os.path.join('feature_requests', f'{request_id}.json')
        with open(feature_file_path, 'w') as f:
            json.dump(feature_request, f, indent=2)
        
        # Also store in memory for quick access
        feature_requests[request_id] = feature_request
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': 'Feature request submitted successfully!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/feature-requests', methods=['GET'])
def get_feature_requests():
    """Get all feature requests with optional filtering"""
    try:
        # Load all feature requests from files
        feature_requests_dir = 'feature_requests'
        requests_list = []
        
        if os.path.exists(feature_requests_dir):
            for filename in os.listdir(feature_requests_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(feature_requests_dir, filename)
                    try:
                        with open(file_path, 'r') as f:
                            req = json.load(f)
                            requests_list.append(req)
                    except:
                        continue
        
        # Sort by votes (descending) then by created_at (descending)
        requests_list.sort(key=lambda x: (-x['votes'], -x['created_at']))
        
        return jsonify({'requests': requests_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/feature-request/<request_id>/vote', methods=['POST'])
def vote_feature_request(request_id):
    """Vote for a feature request"""
    try:
        # Get voter IP as a simple identifier
        voter_ip = request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
        
        # Load feature request from file
        feature_file_path = os.path.join('feature_requests', f'{request_id}.json')
        
        if not os.path.exists(feature_file_path):
            return jsonify({'error': 'Feature request not found'}), 404
        
        with open(feature_file_path, 'r') as f:
            feature_request = json.load(f)
        
        # Check if user already voted
        if voter_ip in feature_request.get('voters', []):
            return jsonify({'error': 'You have already voted for this feature'}), 400
        
        # Add vote
        feature_request['votes'] = feature_request.get('votes', 0) + 1
        if 'voters' not in feature_request:
            feature_request['voters'] = []
        feature_request['voters'].append(voter_ip)
        feature_request['updated_at'] = time.time()
        
        # Save back to file
        with open(feature_file_path, 'w') as f:
            json.dump(feature_request, f, indent=2)
        
        # Update memory cache
        feature_requests[request_id] = feature_request
        
        return jsonify({
            'success': True,
            'votes': feature_request['votes'],
            'message': 'Vote recorded successfully!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@web_app.route('/feature-requests')
def feature_requests_page():
    """Feature requests page with voting interface"""
    return render_template('feature_requests.html')

def require_admin_auth():
    """Simple admin authentication check"""
    # Check for admin key in URL params or session
    admin_key = request.args.get('key') or request.headers.get('X-Admin-Key')
    
    # Get admin key from environment variable (more secure)
    ADMIN_KEY = os.environ.get('ADMIN_KEY', 'default_dev_key_2025')
    
    if admin_key != ADMIN_KEY:
        return False
    return True

@web_app.route('/admin/users')
def admin_users():
    """Admin panel - Users section"""
    if not require_admin_auth():
        return "Admin access required", 401

    try:
        admin_key = request.args.get('key', '')
        conn = user_manager.db.get_connection()

        # Get all users with stats
        users = conn.execute('''
            SELECT
                u.id, u.username, u.email, u.full_name, u.is_active, u.is_admin,
                u.created_at, u.last_login,
                (SELECT COUNT(*) FROM user_activity WHERE user_id = u.id) as activity_count,
                (SELECT COUNT(*) FROM user_sessions WHERE user_id = u.id AND is_active = TRUE) as active_sessions
            FROM users u
            ORDER BY u.created_at DESC
        ''').fetchall()

        # Get conversation counts for each user
        user_data = []
        for user in users:
            conv_dir = os.path.join(CONVERSATIONS_DIR, str(user['id']))
            conversation_count = 0
            if os.path.exists(conv_dir):
                conversation_count = len([f for f in os.listdir(conv_dir) if f.endswith('.json')])

            user_data.append({
                **dict(user),
                'conversation_count': conversation_count
            })

        conn.close()
        return render_template('admin_users.html', users=user_data, admin_key=admin_key)

    except Exception as e:
        return f"Error loading users: {str(e)}", 500

@web_app.route('/admin/analytics')
def admin_analytics():
    """Admin panel - Analytics section"""
    if not require_admin_auth():
        return "Admin access required", 401

    try:
        admin_key = request.args.get('key', '')
        conn = user_manager.db.get_connection()

        # Get analytics data
        total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        active_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE last_login > date("now", "-7 days")').fetchone()['count']
        total_conversations = 0
        total_images = len([f for f in os.listdir(ASSETS_DIR) if os.path.isfile(os.path.join(ASSETS_DIR, f))]) if os.path.exists(ASSETS_DIR) else 0
        total_videos = len([f for f in os.listdir(VIDEOS_DIR) if os.path.isfile(os.path.join(VIDEOS_DIR, f))]) if os.path.exists(VIDEOS_DIR) else 0

        # Count all conversations
        if os.path.exists(CONVERSATIONS_DIR):
            for user_dir in os.listdir(CONVERSATIONS_DIR):
                user_path = os.path.join(CONVERSATIONS_DIR, user_dir)
                if os.path.isdir(user_path):
                    total_conversations += len([f for f in os.listdir(user_path) if f.endswith('.json')])

        # Get recent activity
        recent_activity = conn.execute('''
            SELECT ua.*, u.username, u.email
            FROM user_activity ua
            JOIN users u ON ua.user_id = u.id
            ORDER BY ua.created_at DESC
            LIMIT 50
        ''').fetchall()

        # Get activity by type
        activity_by_type = conn.execute('''
            SELECT activity_type, COUNT(*) as count
            FROM user_activity
            GROUP BY activity_type
            ORDER BY count DESC
        ''').fetchall()

        conn.close()

        analytics_data = {
            'total_users': total_users,
            'active_users': active_users,
            'total_conversations': total_conversations,
            'total_images': total_images,
            'total_videos': total_videos,
            'recent_activity': [dict(row) for row in recent_activity],
            'activity_by_type': [dict(row) for row in activity_by_type]
        }

        return render_template('admin_analytics.html', analytics=analytics_data, admin_key=admin_key)

    except Exception as e:
        return f"Error loading analytics: {str(e)}", 500

@web_app.route('/admin/settings')
def admin_settings():
    """Admin panel - Settings section"""
    if not require_admin_auth():
        return "Admin access required", 401

    try:
        admin_key = request.args.get('key', '')

        # Get system info
        settings_data = {
            'admin_key': os.environ.get('ADMIN_KEY', 'default_dev_key_2025'),
            'environment': 'Production' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Development',
            'data_dir': DATA_DIR,
            'upload_folder': web_app.config['UPLOAD_FOLDER'],
            'assets_dir': ASSETS_DIR,
            'videos_dir': VIDEOS_DIR,
            'conversations_dir': CONVERSATIONS_DIR,
            'database_path': DATABASE_PATH,
            'api_keys': {
                'openai': bool(os.environ.get('OPENAI_API_KEY')),
                'fal': bool(os.environ.get('FAL_KEY')),
                'tavily': bool(os.environ.get('TAVILY_API_KEY'))
            }
        }

        return render_template('admin_settings.html', settings=settings_data, admin_key=admin_key)

    except Exception as e:
        return f"Error loading settings: {str(e)}", 500

@web_app.route('/admin/files')
def file_browser():
    """Simple file browser for viewing generated assets"""
    # Simple authentication check
    if not require_admin_auth():
        return """
        <html>
        <head><title>Admin Access Required</title></head>
        <body style="font-family: -apple-system, sans-serif; padding: 50px; text-align: center;">
            <h2>🔒 Admin Access Required</h2>
            <p>Add <code>?key=YOUR_ADMIN_KEY</code> to the URL to access the file browser.</p>
            <p><strong>Example:</strong> <code>/admin/files?key=YOUR_ADMIN_KEY</code></p>
            <p><small>Contact the administrator for the admin key.</small></p>
        </body>
        </html>
        """, 401
    
    try:
        # Get admin key for passing to view URLs
        admin_key = request.args.get('key', '')
        
        # Get files from all directories
        file_data = {}
        # Directory mapping: (actual_path, display_name)
        directory_mapping = [
            (ASSETS_DIR, 'Generated Images'),
            (VIDEOS_DIR, 'Generated Videos'), 
            (web_app.config['UPLOAD_FOLDER'], 'User Uploads'),
            ('shared', 'Shared Content'),
            ('feature_requests', 'Feature Requests'),
            (CONVERSATIONS_DIR, 'User Conversations')
        ]
        
        for directory_path, display_name in directory_mapping:
            if os.path.exists(directory_path):
                files = []
                print(f"Admin Debug: Processing {display_name} at {directory_path}")
                
                if directory_path == CONVERSATIONS_DIR:
                    # Special handling for conversations - look in user directories
                    for user_dir in os.listdir(directory_path):
                        user_path = os.path.join(directory_path, user_dir)
                        if os.path.isdir(user_path):
                            for filename in os.listdir(user_path):
                                file_path = os.path.join(user_path, filename)
                                if os.path.isfile(file_path) and filename.endswith('.json'):
                                    stat = os.stat(file_path)
                                    
                                    # Try to read conversation metadata
                                    conversation_data = None
                                    try:
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            conversation_data = json.load(f)
                                    except:
                                        pass
                                    
                                    conversation_id = conversation_data.get('id') if conversation_data else filename[:-5]
                                    files.append({
                                        'name': filename,
                                        'size': stat.st_size,
                                        'modified': stat.st_mtime,
                                        'user_id': user_dir,
                                        'full_path': f'{directory_path}/{user_dir}/{filename}',
                                        'url': f'/admin/view-conversation/{user_dir}/{conversation_id}?key={admin_key}',  # Now viewable!
                                        'conversation_title': conversation_data.get('title', 'Untitled') if conversation_data else 'Untitled',
                                        'message_count': len(conversation_data.get('messages', [])) if conversation_data else 0,
                                        'last_updated': conversation_data.get('lastUpdated') if conversation_data else None,
                                        'conversation_id': conversation_id
                                    })
                else:
                    # Standard file handling for other directories
                    for filename in os.listdir(directory_path):
                        file_path = os.path.join(directory_path, filename)
                        if os.path.isfile(file_path):
                            stat = os.stat(file_path)
                            # Determine URL based on directory type
                            file_url = None
                            if directory_path == ASSETS_DIR:
                                file_url = f'/assets/{filename}'
                            elif directory_path == VIDEOS_DIR:
                                file_url = f'/videos/{filename}'
                            elif directory_path == web_app.config['UPLOAD_FOLDER']:
                                file_url = f'/uploads/{filename}'
                            elif directory_path == 'shared' and filename.endswith('.json'):
                                # Shared content - create view URL
                                share_id = filename[:-5]  # Remove .json extension
                                file_url = f'/admin/view-shared/{share_id}?key={admin_key}'
                            elif directory_path == 'feature_requests' and filename.endswith('.json'):
                                # Feature requests - could add view URL later
                                file_url = None
                            
                            files.append({
                                'name': filename,
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'url': file_url
                            })
                
                # Sort files by modification time (newest first)
                files.sort(key=lambda x: x['modified'], reverse=True)
                # Use display_name as key for template (works for both conversation and standard directories)
                file_data[display_name] = files
            else:
                print(f"Admin Debug: Directory does not exist: {display_name} at {directory_path}")
                # Still add empty entry so it shows in the admin panel
                file_data[display_name] = []
        
        return render_template('file_browser.html', file_data=file_data, admin_key=admin_key)
        
    except Exception as e:
        return f"Error browsing files: {str(e)}", 500

@web_app.route('/admin/view-conversation/<user_id>/<conversation_id>')
def view_conversation(user_id, conversation_id):
    """View a conversation in admin panel"""
    # Simple authentication check
    if not require_admin_auth():
        return "Admin access required", 401
    
    try:
        conv_file_path = os.path.join(CONVERSATIONS_DIR, user_id, f'{conversation_id}.json')
        if not os.path.exists(conv_file_path):
            return f"Conversation not found: {conv_file_path}", 404
        
        with open(conv_file_path, 'r', encoding='utf-8') as f:
            conversation_data = json.load(f)
        
        return render_template('admin_conversation_view.html', 
                             conversation=conversation_data, 
                             user_id=user_id,
                             conversation_id=conversation_id)
        
    except Exception as e:
        return f"Error viewing conversation: {str(e)}", 500

@web_app.route('/admin/view-shared/<share_id>')
def view_shared_content(share_id):
    """View shared content in admin panel"""
    # Simple authentication check
    if not require_admin_auth():
        return "Admin access required", 401
    
    try:
        shared_file_path = os.path.join('shared', f'{share_id}.json')
        if not os.path.exists(shared_file_path):
            return f"Shared content not found: {shared_file_path}", 404
        
        with open(shared_file_path, 'r', encoding='utf-8') as f:
            shared_data = json.load(f)
        
        return render_template('admin_shared_view.html', 
                             shared_content=shared_data,
                             share_id=share_id)
        
    except Exception as e:
        return f"Error viewing shared content: {str(e)}", 500

@web_app.route('/admin/delete-file', methods=['POST'])
def delete_file():
    """Delete a file (with simple protection)"""
    # Simple authentication check
    if not require_admin_auth():
        return jsonify({'error': 'Admin access required'}), 401

    try:
        data = request.get_json()
        file_path = data.get('file_path', '')

        # Security check: only allow deleting files in allowed directories
        allowed_dirs = ['assets', 'videos', 'uploads']
        if not any(file_path.startswith(d + '/') for d in allowed_dirs):
            return jsonify({'error': 'Access denied'}), 403

        # Additional security: no path traversal
        if '..' in file_path or file_path.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400

        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': f'File {file_path} deleted successfully'})
        else:
            return jsonify({'error': 'File not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# SEO OPTIMIZATION ROUTES
# =============================================================================

@web_app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engine crawlers"""
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')

@web_app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml for search engine indexing"""
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')

@web_app.route('/sitemap-dynamic.xml')
def sitemap_dynamic():
    """Generate dynamic sitemap with recent conversations and blog posts"""
    from datetime import datetime

    sitemap_entries = []

    # Add main pages
    base_pages = [
        ('https://aiezzy.com/', '2025-10-22', 'daily', '1.0'),
        ('https://aiezzy.com/ai-image-generator', '2025-10-22', 'weekly', '0.9'),
        ('https://aiezzy.com/text-to-video', '2025-10-22', 'weekly', '0.9'),
        ('https://aiezzy.com/pdf-converter', '2025-10-22', 'weekly', '0.9'),
    ]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for url, lastmod, changefreq, priority in base_pages:
        xml.append('  <url>')
        xml.append(f'    <loc>{url}</loc>')
        xml.append(f'    <lastmod>{lastmod}</lastmod>')
        xml.append(f'    <changefreq>{changefreq}</changefreq>')
        xml.append(f'    <priority>{priority}</priority>')
        xml.append('  </url>')

    xml.append('</urlset>')

    return '\n'.join(xml), 200, {'Content-Type': 'application/xml'}

# SEO Landing Pages
@web_app.route('/ai-image-generator')
def ai_image_generator_page():
    """SEO-optimized landing page for AI image generation"""
    try:
        return render_template('landing/ai_image_generator.html')
    except:
        return redirect('/')

@web_app.route('/text-to-video')
def text_to_video_page():
    """SEO-optimized landing page for text-to-video"""
    try:
        return render_template('landing/text_to_video.html')
    except:
        return redirect('/')

@web_app.route('/image-to-video')
def image_to_video_page():
    """SEO-optimized landing page for image-to-video"""
    return redirect('/')

@web_app.route('/pdf-converter')
def pdf_converter_page():
    """SEO-optimized landing page for PDF conversion"""
    try:
        return render_template('landing/pdf_converter.html')
    except:
        return redirect('/')

@web_app.route('/word-to-pdf')
def word_to_pdf_page():
    """SEO-optimized landing page for Word to PDF conversion - 201K searches/month"""
    try:
        return render_template('landing/word-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-word')
def pdf_to_word_page():
    """SEO-optimized landing page for PDF to Word conversion - 135K searches/month"""
    try:
        return render_template('landing/pdf-to-word.html')
    except:
        return redirect('/')

@web_app.route('/excel-to-pdf')
def excel_to_pdf_page():
    """SEO-optimized landing page for Excel to PDF conversion - 90.5K searches/month"""
    try:
        return render_template('landing/excel-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-excel')
def pdf_to_excel_page():
    """SEO-optimized landing page for PDF to Excel conversion - 74K searches/month"""
    try:
        return render_template('landing/pdf-to-excel.html')
    except:
        return redirect('/')

@web_app.route('/jpg-to-pdf')
def jpg_to_pdf_page():
    """SEO-optimized landing page for JPG to PDF conversion - 60.5K searches/month"""
    try:
        return render_template('landing/jpg-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-jpg')
def pdf_to_jpg_page():
    """SEO-optimized landing page for PDF to JPG conversion - 49.5K searches/month"""
    try:
        return render_template('landing/pdf-to-jpg.html')
    except:
        return redirect('/')

@web_app.route('/png-to-pdf')
def png_to_pdf_page():
    """SEO-optimized landing page for PNG to PDF conversion - 40.5K searches/month"""
    try:
        return render_template('landing/png-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-png')
def pdf_to_png_page():
    """SEO-optimized landing page for PDF to PNG conversion - 33.1K searches/month"""
    try:
        return render_template('landing/pdf-to-png.html')
    except:
        return redirect('/')

@web_app.route('/ppt-to-pdf')
def ppt_to_pdf_page():
    """SEO-optimized landing page for PowerPoint to PDF conversion - 27.1K searches/month"""
    try:
        return render_template('landing/ppt-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-ppt')
def pdf_to_ppt_page():
    """SEO-optimized landing page for PDF to PowerPoint conversion - 22.2K searches/month"""
    try:
        return render_template('landing/pdf-to-ppt.html')
    except:
        return redirect('/')

@web_app.route('/docx-to-pdf')
def docx_to_pdf_page():
    """SEO-optimized landing page for DOCX to PDF conversion - 45K searches/month"""
    try:
        return render_template('landing/docx-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-text')
def pdf_to_text_page():
    """SEO-optimized landing page for PDF to Text conversion - 40K searches/month"""
    try:
        return render_template('landing/pdf-to-text.html')
    except:
        return redirect('/')

@web_app.route('/compress-pdf')
def compress_pdf_page():
    """SEO-optimized landing page for PDF compression - 35K searches/month"""
    try:
        return render_template('landing/compress-pdf.html')
    except:
        return redirect('/')

@web_app.route('/merge-pdf')
def merge_pdf_page():
    """SEO-optimized landing page for PDF merging - 30K searches/month"""
    try:
        return render_template('landing/merge-pdf.html')
    except:
        return redirect('/')

@web_app.route('/split-pdf')
def split_pdf_page():
    """SEO-optimized landing page for PDF splitting - 25K searches/month"""
    try:
        return render_template('landing/split-pdf.html')
    except:
        return redirect('/')

@web_app.route('/rotate-pdf')
def rotate_pdf_page():
    """SEO-optimized landing page for PDF rotation - 18K searches/month"""
    try:
        return render_template('landing/rotate-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-csv')
def pdf_to_csv_page():
    """SEO-optimized landing page for PDF to CSV conversion - 15K searches/month"""
    try:
        return render_template('landing/pdf-to-csv.html')
    except:
        return redirect('/')

@web_app.route('/csv-to-pdf')
def csv_to_pdf_page():
    """SEO-optimized landing page for CSV to PDF conversion - 12K searches/month"""
    try:
        return render_template('landing/csv-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/html-to-pdf')
def html_to_pdf_page():
    """SEO-optimized landing page for HTML to PDF conversion - 10K searches/month"""
    try:
        return render_template('landing/html-to-pdf.html')
    except:
        return redirect('/')

@web_app.route('/pdf-to-html')
def pdf_to_html_page():
    """SEO-optimized landing page for PDF to HTML conversion - 8K searches/month"""
    try:
        return render_template('landing/pdf-to-html.html')
    except:
        return redirect('/')

# IMAGE CONVERSION LANDING PAGES (Oct 2025 - 1.3M monthly searches!)
@web_app.route('/resize-image')
def resize_image_page():
    """SEO-optimized landing page for image resizing - 500K searches/month"""
    try:
        return render_template('landing/resize-image.html')
    except:
        return redirect('/')

@web_app.route('/compress-image')
def compress_image_page():
    """SEO-optimized landing page for image compression - 300K searches/month"""
    try:
        return render_template('landing/compress-image.html')
    except:
        return redirect('/')

@web_app.route('/jpeg-to-png')
def jpeg_to_png_page():
    """SEO-optimized landing page for JPEG to PNG conversion - 200K searches/month"""
    try:
        return render_template('landing/jpeg-to-png.html')
    except:
        return redirect('/')

@web_app.route('/png-to-jpeg')
def png_to_jpeg_page():
    """SEO-optimized landing page for PNG to JPEG conversion - 150K searches/month"""
    try:
        return render_template('landing/png-to-jpeg.html')
    except:
        return redirect('/')

@web_app.route('/webp-to-png')
def webp_to_png_page():
    """SEO-optimized landing page for WEBP to PNG conversion - 60K searches/month"""
    try:
        return render_template('landing/webp-to-png.html')
    except:
        return redirect('/')

@web_app.route('/webp-to-jpeg')
def webp_to_jpeg_page():
    """SEO-optimized landing page for WEBP to JPEG conversion - 50K searches/month"""
    try:
        return render_template('landing/webp-to-jpeg.html')
    except:
        return redirect('/')

@web_app.route('/heic-to-jpeg')
def heic_to_jpeg_page():
    """SEO-optimized landing page for HEIC to JPEG conversion - 40K searches/month"""
    try:
        return render_template('landing/heic-to-jpeg.html')
    except:
        return redirect('/')

@web_app.route('/gif-to-png')
def gif_to_png_page():
    """SEO-optimized landing page for GIF to PNG conversion - 25K searches/month"""
    try:
        return render_template('landing/gif-to-png.html')
    except:
        return redirect('/')

# PHASE 1 & 2 LANDING PAGES (Oct 2025 - 1.65M monthly searches!)
@web_app.route('/qr-code-generator')
def qr_code_generator_page():
    """SEO-optimized landing page for QR code generator - 300K searches/month"""
    try:
        return render_template('landing/qr-code-generator.html')
    except:
        return redirect('/')

@web_app.route('/word-counter')
def word_counter_page():
    """SEO-optimized landing page for word counter - 200K searches/month"""
    try:
        return render_template('landing/word-counter.html')
    except:
        return redirect('/')

@web_app.route('/video-to-gif')
def video_to_gif_page():
    """SEO-optimized landing page for video to GIF converter - 200K searches/month"""
    try:
        return render_template('landing/video-to-gif.html')
    except:
        return redirect('/')

@web_app.route('/mp4-to-mp3')
def mp4_to_mp3_page():
    """SEO-optimized landing page for MP4 to MP3 converter - 150K searches/month"""
    try:
        return render_template('landing/mp4-to-mp3.html')
    except:
        return redirect('/')

@web_app.route('/case-converter')
def case_converter_page():
    """SEO-optimized landing page for case converter - 100K searches/month"""
    try:
        return render_template('landing/case-converter.html')
    except:
        return redirect('/')

@web_app.route('/barcode-generator')
def barcode_generator_page():
    """SEO-optimized landing page for barcode generator - 100K searches/month"""
    try:
        return render_template('landing/barcode-generator.html')
    except:
        return redirect('/')

@web_app.route('/audio-converter')
def audio_converter_page():
    """SEO-optimized landing page for audio converter - 100K searches/month"""
    try:
        return render_template('landing/audio-converter.html')
    except:
        return redirect('/')

@web_app.route('/compress-video')
def compress_video_page():
    """SEO-optimized landing page for video compressor - 80K searches/month"""
    try:
        return render_template('landing/compress-video.html')
    except:
        return redirect('/')

@web_app.route('/compress-audio')
def compress_audio_page():
    """SEO-optimized landing page for audio compressor - 80K searches/month"""
    try:
        return render_template('landing/compress-audio.html')
    except:
        return redirect('/')

@web_app.route('/text-formatter')
def text_formatter_page():
    """SEO-optimized landing page for text formatter - 80K searches/month"""
    try:
        return render_template('landing/text-formatter.html')
    except:
        return redirect('/')

@web_app.route('/lorem-ipsum-generator')
def lorem_ipsum_generator_page():
    """SEO-optimized landing page for Lorem Ipsum generator - 50K searches/month"""
    try:
        return render_template('landing/lorem-ipsum-generator.html')
    except:
        return redirect('/')

@web_app.route('/password-generator')
def password_generator_page():
    """SEO-optimized landing page for password generator - 40K searches/month"""
    try:
        return render_template('landing/password-generator.html')
    except:
        return redirect('/')

@web_app.route('/trim-audio')
def trim_audio_page():
    """SEO-optimized landing page for audio trimmer - 40K searches/month"""
    try:
        return render_template('landing/trim-audio.html')
    except:
        return redirect('/')

@web_app.route('/trim-video')
def trim_video_page():
    """SEO-optimized landing page for video trimmer - 40K searches/month"""
    try:
        return render_template('landing/trim-video.html')
    except:
        return redirect('/')

@web_app.route('/change-video-speed')
def change_video_speed_page():
    """SEO-optimized landing page for video speed changer - 30K searches/month"""
    try:
        return render_template('landing/change-video-speed.html')
    except:
        return redirect('/')

@web_app.route('/multi-image-fusion')
def multi_image_fusion_page():
    """SEO-optimized landing page for multi-image fusion"""
    return redirect('/')

@web_app.route('/ai-image-editor')
def ai_image_editor_page():
    """SEO-optimized landing page for AI image editing"""
    return redirect('/')

@web_app.route('/chatgpt-alternative')
def chatgpt_alternative_page():
    """SEO-optimized landing page for ChatGPT alternative - 90.5K searches/month"""
    try:
        return render_template('landing/chatgpt-alternative.html')
    except:
        return redirect('/')

@web_app.route('/tools')
def tools_page():
    """SEO-optimized tools directory page"""
    return redirect('/')

@web_app.route('/about')
def about_page():
    """About AIezzy page"""
    return redirect('/')

@web_app.route('/blog')
def blog_page():
    """Blog listing page"""
    return redirect('/')

@web_app.route('/pricing')
def pricing_page():
    """Pricing page (free forever)"""
    return redirect('/')

@web_app.route('/faq')
def faq_page():
    """FAQ page with structured data"""
    return redirect('/')

# === PERMANENT FILE LINKS SERVING (CATCH-ALL ROUTE - MUST BE LAST!) =========

@web_app.route('/<path:short_path>')
def serve_permanent_file(short_path):
    """
    Serve permanent files with short URLs like:
    - /abc123xyz456.png
    - /f5h39dhekl79e.gif

    IMPORTANT: This catch-all route MUST be defined last to avoid
    intercepting other specific routes.
    """
    try:
        # Extract short_id from path (remove extension if present)
        if '.' in short_path:
            short_id = short_path.rsplit('.', 1)[0]
        else:
            short_id = short_path

        # Check if this is a permanent file
        db = load_permanent_files_db()
        if short_id in db:
            file_info = db[short_id]

            # Increment view counter
            file_info['views'] = file_info.get('views', 0) + 1
            save_permanent_files_db(db)

            # Serve the file
            filename = file_info['filename']
            return send_from_directory(PERMANENT_FILES_DIR, filename)

        # If not a permanent file, return 404
        from werkzeug.exceptions import NotFound
        raise NotFound()

    except NotFound:
        raise
    except Exception as e:
        from werkzeug.exceptions import NotFound
        raise NotFound()

# ==============================================================================

if __name__ == '__main__':
    # Submit key pages to IndexNow for instant indexing on startup
    print("Submitting key pages to IndexNow for instant search engine indexing...")
    submit_key_pages_to_indexnow()

    port = int(os.environ.get('PORT', 5000))
    web_app.run(debug=False, host='0.0.0.0', port=port)