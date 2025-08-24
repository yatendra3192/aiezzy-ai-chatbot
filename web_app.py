from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import base64
import uuid
import time
import json
import secrets
from werkzeug.utils import secure_filename
from app import app as langgraph_app, encode_image_to_content_block, set_recent_image_path, clear_thread_cache, clear_thread_context, reset_all_context, set_current_thread_id

# Initialize Flask app
web_app = Flask(__name__)
web_app.config['UPLOAD_FOLDER'] = 'uploads'
web_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Store recent images for editing reference
recent_images = {}
# Store the most recent image per thread for editing context
thread_image_context = {}
# Store shared conversations
shared_conversations = {}
# Store feature requests
feature_requests = {}
# Store user conversations persistently
user_conversations = {}

# Create conversations directory for server-side storage
os.makedirs('conversations', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
def index():
    return render_template('modern_chat.html')

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
        
        # CRITICAL FIX: If this is a new conversation (no history), clear any old image context
        if not history or len(history) == 0:
            clear_thread_context(thread_id)
            # Also clear web_app level context
            if thread_id in thread_image_context:
                del thread_image_context[thread_id]
            # ADDITIONAL FIX: Reset the global current thread ID to prevent cross-conversation contamination
            reset_all_context()
            print(f"NEW CONVERSATION FIX: Cleared all global context for fresh start")
        
        # ENHANCED FIX: Also clear context when starting multi-step tasks to prevent contamination
        is_multi_step_start = any(keyword in message.lower() for keyword in ['create', 'combine', 'generate', 'make']) and len(message.split('.')) >= 2
        if is_multi_step_start and len(history) <= 1:
            clear_thread_context(thread_id)
            reset_all_context()
            print(f"MULTI-STEP START FIX: Cleared context for clean multi-step execution")
        
        # DEBUG: Log what history is being sent
        print(f"DEBUG HISTORY: thread_id={thread_id}, history_length={len(history) if history else 0}")
        if history:
            print(f"DEBUG HISTORY: first_msg={history[0] if len(history) > 0 else 'none'}")
            print(f"DEBUG HISTORY: last_msg={history[-1] if len(history) > 0 else 'none'}")
        
        # Check if this is a multi-step request and which step we're on
        is_multi_step = detect_multi_step_request(message, history)
        current_step = determine_current_step(message, history)
        
        # Check if this is an image editing request and we have context
        edit_keywords = ['edit', 'change', 'modify', 'add', 'remove', 'alter', 'fix', 'replace', 'put', 'place', 'behind', 'explosion', 'fire', 'background', 'foreground', 'text', 'overlay']
        is_edit_request = any(word in message.lower() for word in edit_keywords)
        has_image_context = thread_id in thread_image_context
        
        # For image editing requests, add context to prevent cached responses
        if is_edit_request and has_image_context:
            pass  # We'll handle this through message formatting instead
        
        # Also check if the history contains an image path we can use
        image_path_from_history = None
        for msg in reversed(history):  # Check recent messages for image paths
            if msg.get('hasImage') and msg.get('imagePath'):
                image_path_from_history = msg.get('imagePath')
                break
        
        # If it's an edit request, try to set the image path from various sources
        if is_edit_request:
            context_set = False
            import sys
            print(f"EDIT DEBUG: is_edit_request=True, has_image_context={has_image_context}", file=sys.stderr)
            print(f"EDIT DEBUG: thread_image_context keys: {list(thread_image_context.keys())}", file=sys.stderr)
            print(f"EDIT DEBUG: current thread_id: {thread_id}", file=sys.stderr)
            if has_image_context:
                set_recent_image_path(thread_image_context[thread_id], thread_id)
                print(f"EDIT FIX: Using web_app context: {thread_image_context[thread_id]}")
                context_set = True
            elif image_path_from_history:
                set_recent_image_path(image_path_from_history, thread_id)
                # Also update the thread context for future use
                if thread_id:
                    thread_image_context[thread_id] = image_path_from_history
                print(f"EDIT FIX: Using history context: {image_path_from_history}")
                context_set = True
            
            # ADDITIONAL FIX: Look for recent image patterns in history content
            if not context_set:
                for msg in reversed(history):
                    content = msg.get('content', '')
                    if 'assets/' in content and '.png' in content:
                        import re
                        asset_match = re.search(r'/assets/([\w_]+\.png)', content)
                        if asset_match:
                            asset_path = f"assets/{asset_match.group(1)}"
                            if os.path.exists(asset_path):
                                set_recent_image_path(asset_path, thread_id)
                                thread_image_context[thread_id] = asset_path
                                print(f"EDIT FIX: Found image in content: {asset_path}")
                                context_set = True
                                break
            
            if not context_set:
                print(f"WARNING: No image context found for edit request in thread {thread_id}")
        
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
        
        # Add current message with context for image editing to ensure accurate responses
        if is_edit_request and has_image_context:
            current_timestamp = int(time.time())
            # CONTEXT RESET: Add system message to prevent referencing old context
            if len(history) <= 4:  # Likely a fresh conversation
                messages.append({"role": "system", "content": "You are starting fresh with this image editing request. Focus only on the current image and edit request without referencing previous conversations or context."})
            enhanced_message = f"{message} - Please be specific about this exact edit in your response. Request timestamp: {current_timestamp}"
            messages.append({"role": "user", "content": enhanced_message})
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
        
        # DEBUG: Log the actual response content to see what we're working with
        import sys
        print(f"DEBUG RESPONSE: {response_content}", file=sys.stderr)
        print(f"DEBUG: Looking for 'Image saved to' pattern", file=sys.stderr)
        
        # ROBUST FIX: Extract image path from HTML src attribute instead of relying on text
        import re
        img_match = re.search(r'<img[^>]*src="/assets/([^"]+)"', response_content)
        if img_match:
            filename = img_match.group(1)
            generated_image_path = f"assets/{filename}"
            thread_image_context[thread_id] = generated_image_path
            import sys
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
                generated_image_path = path_match.group(1).strip()
                thread_image_context[thread_id] = generated_image_path
                import sys
                print(f"LEGACY: Updated thread {thread_id} context with generated image: {generated_image_path}", file=sys.stderr)
                
                # CRITICAL FIX: Also sync with app.py's thread context for editing
                set_recent_image_path(generated_image_path, thread_id)
                print(f"LEGACY: Updated app.py thread context for {thread_id}: {generated_image_path}", file=sys.stderr)
        
        # ADDITIONAL FIX: Also handle edited images
        if 'Image edit completed:' in response_content:
            import re
            path_match = re.search(r'Saved as (.*?)(?:\s|$)', response_content)
            if path_match:
                edited_image_path = path_match.group(1).strip()
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
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/analyze-image', methods=['POST'])
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
        
        if len(uploaded_files) > 5:
            return jsonify({'error': 'Maximum 5 images allowed'}), 400
        
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
            
            # Create content block for the image
            img_block = encode_image_to_content_block(file_path, mime_type)
            
            # Store image path for potential editing - CRITICAL DEBUG
            recent_images[thread_id] = file_path
            thread_image_context[thread_id] = file_path
            set_recent_image_path(file_path, thread_id)
            print(f"DEBUG: Set image path for thread {thread_id}: {file_path}")
            print(f"DEBUG: File exists: {os.path.exists(file_path)}")
            
            user_msg = {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    img_block,
                ],
            }
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
    return send_from_directory('assets', filename)

@web_app.route('/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

@web_app.route('/logo.png')
def serve_logo():
    return send_from_directory('.', 'logo.png')

@web_app.route('/favicon.png')
def serve_favicon():
    return send_from_directory('.', 'favicon.png')

@web_app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory('videos', filename)

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
def save_conversation():
    """Save a conversation to server-side storage for persistence"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        conversation_data = data.get('conversation_data')
        user_id = data.get('user_id', 'default_user')  # For future user authentication
        
        if not conversation_id or not conversation_data:
            return jsonify({'error': 'Missing conversation_id or conversation_data'}), 400
        
        # Create user-specific conversation directory
        user_conv_dir = os.path.join('conversations', user_id)
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
def load_conversations():
    """Load all conversations for a user from server-side storage"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Load from memory first
        if user_id in user_conversations:
            conversations = user_conversations[user_id]
        else:
            conversations = {}
            
        # Load from files if not in memory
        user_conv_dir = os.path.join('conversations', user_id)
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
def get_conversation(conversation_id):
    """Get a specific conversation by ID"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Check memory first
        if user_id in user_conversations and conversation_id in user_conversations[user_id]:
            conversation = user_conversations[user_id][conversation_id]
        else:
            # Load from file
            conv_file_path = os.path.join('conversations', user_id, f'{conversation_id}.json')
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
def delete_conversation(conversation_id):
    """Delete a conversation from server storage"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Remove from memory
        if user_id in user_conversations and conversation_id in user_conversations[user_id]:
            del user_conversations[user_id][conversation_id]
        
        # Remove file
        conv_file_path = os.path.join('conversations', user_id, f'{conversation_id}.json')
        if os.path.exists(conv_file_path):
            os.remove(conv_file_path)
            return jsonify({'success': True, 'message': 'Conversation deleted'})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
            
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500

@web_app.route('/api/export-conversation/<conversation_id>')
def export_conversation(conversation_id):
    """Export a conversation as JSON, Markdown, or HTML"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        export_format = request.args.get('format', 'json').lower()
        
        # Get conversation data
        conv_file_path = os.path.join('conversations', user_id, f'{conversation_id}.json')
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
def export_all_conversations():
    """Export all conversations as a ZIP file"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        export_format = request.args.get('format', 'json').lower()
        
        import zipfile
        from io import BytesIO
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            user_conv_dir = os.path.join('conversations', user_id)
            
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
        # Get files from all directories
        file_data = {}
        directories = ['assets', 'videos', 'uploads', 'shared', 'feature_requests', 'conversations']
        
        for directory in directories:
            if os.path.exists(directory):
                files = []
                
                if directory == 'conversations':
                    # Special handling for conversations - look in user directories
                    for user_dir in os.listdir(directory):
                        user_path = os.path.join(directory, user_dir)
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
                                    
                                    files.append({
                                        'name': filename,
                                        'size': stat.st_size,
                                        'modified': stat.st_mtime,
                                        'user_id': user_dir,
                                        'full_path': f'{directory}/{user_dir}/{filename}',
                                        'url': None,  # Conversations are not directly servable
                                        'conversation_title': conversation_data.get('title', 'Untitled') if conversation_data else 'Untitled',
                                        'message_count': len(conversation_data.get('messages', [])) if conversation_data else 0,
                                        'last_updated': conversation_data.get('lastUpdated') if conversation_data else None,
                                        'conversation_id': conversation_data.get('id') if conversation_data else filename[:-5]
                                    })
                else:
                    # Standard file handling for other directories
                    for filename in os.listdir(directory):
                        file_path = os.path.join(directory, filename)
                        if os.path.isfile(file_path):
                            stat = os.stat(file_path)
                            files.append({
                                'name': filename,
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'url': f'/{directory}/{filename}' if directory in ['assets', 'videos', 'uploads'] else None
                            })
                
                # Sort files by modification time (newest first)
                files.sort(key=lambda x: x['modified'], reverse=True)
                file_data[directory] = files
        
        return render_template('file_browser.html', file_data=file_data)
        
    except Exception as e:
        return f"Error browsing files: {str(e)}", 500

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    web_app.run(debug=False, host='0.0.0.0', port=port)