from __future__ import annotations

import os, base64, time, pathlib
from typing import Annotated, List

from dotenv import load_dotenv
load_dotenv()

# LangGraph / LangChain
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.runnables import RunnableConfig

# Note: OpenAI client removed since we now use nano-banana for image generation

# FAL AI client for image editing
import fal_client
fal_client.api_key = os.getenv("FAL_KEY")

# PDF Converter for document processing
import pdf_converter

# Image Converter for image format conversions
import image_converter

# Phase 1 & 2 Tools (Oct 2025)
import text_tools
import qr_barcode_tools
# TEMPORARILY DISABLED - causing deployment issues
# import audio_tools
# import video_tools

# Configure persistent storage paths for Railway
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production: Use Railway persistent volume
    DATA_DIR = pathlib.Path('/app/data')
    ASSETS_DIR = DATA_DIR / 'assets'
    VIDEOS_DIR = DATA_DIR / 'videos'
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
else:
    # Development: Use local directories
    ASSETS_DIR = pathlib.Path("assets")
    VIDEOS_DIR = pathlib.Path("videos")

ASSETS_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)

# --- Helpers ---------------------------------------------------------------

def save_video_from_url(video_url: str) -> str:
    """Download and save video from URL"""
    import requests
    response = requests.get(video_url)
    if response.status_code == 200:
        video_path = VIDEOS_DIR / f"video_{int(time.time())}.mp4"
        video_path.write_bytes(response.content)
        return str(video_path)
    else:
        raise Exception(f"Failed to download video: {response.status_code}")

# --- Tool: web search for real-time information ---------------------------
@tool
def search_web(query: str) -> str:
    """
    Search the web for current information, news, and real-time data using Tavily AI.
    Use this when users ask for current events, latest information, or data that might have changed recently.
    """
    try:
        from tavily import TavilyClient
        
        # Get Tavily API key from environment
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        if not tavily_api_key:
            return "Web search unavailable: Tavily API key not configured. Please add TAVILY_API_KEY to your .env file."
        
        # Initialize Tavily client
        tavily = TavilyClient(api_key=tavily_api_key)
        
        # Add current date context to improve relevance
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")  # August 13, 2025
        
        # Enhance query with date context for current information
        enhanced_query = f"{query} {current_date} current latest today"
        
        # Perform search with Tavily - optimized for AI agents
        try:
            search_result = tavily.search(
                query=enhanced_query,
                search_depth="advanced",  # Use advanced for more recent results
                max_results=5,            # Number of search results
                include_answer=True,      # Include AI-generated answer
                include_raw_content=False,  # Don't include raw HTML
                include_images=False,     # Don't include images for now
                days=7                    # Try to get results from last 7 days
            )
        except Exception:
            # Fallback without days parameter if not supported
            search_result = tavily.search(
                query=enhanced_query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
                include_raw_content=False,
                include_images=False
            )
        
        # Format the results
        formatted_results = f"**Web Search Results for: '{query}'** *(as of {current_date})*\n\n"
        
        # Add AI-generated answer if available
        if search_result.get('answer'):
            formatted_results += f"**Current Summary:**\n{search_result['answer']}\n\n"
        
        # Add search results
        if search_result.get('results'):
            formatted_results += "**Sources:**\n"
            for i, result in enumerate(search_result['results'][:3], 1):  # Show top 3 results
                title = result.get('title', 'No title')
                content = result.get('content', 'No content available')
                url = result.get('url', '')
                
                # Truncate content if too long
                if len(content) > 200:
                    content = content[:200] + "..."
                
                formatted_results += f"\n**{i}. {title}**\n"
                formatted_results += f"{content}\n"
                if url:
                    formatted_results += f"*Source: {url}*\n"
        
        return formatted_results
        
    except ImportError:
        return "Web search error: Tavily package not installed. Run: pip install tavily-python"
    except Exception as e:
        return f"Web search error: {str(e)}"

# --- Tool: external image generation (FAL AI nano-banana) ------------------
@tool
def generate_image(prompt: str,
                  num_images: int = 1,
                  state: Annotated[dict, InjectedState] = None) -> str:
    """
    Generate an image from a text prompt using FAL AI nano-banana.
    Returns HTML img tag for web display.
    """
    result = fal_client.subscribe(
        "fal-ai/nano-banana",
        arguments={
            "prompt": prompt,
            "num_images": num_images
        },
        with_logs=True
    )
    
    if result and result.get('images') and len(result['images']) > 0:
        image_url = result['images'][0]['url']
        
        # Download and save the image locally
        import requests
        response = requests.get(image_url)
        if response.status_code == 200:
            # Use microsecond precision to avoid filename collisions when called rapidly
            import time
            timestamp = int(time.time() * 1000000)  # Microsecond timestamp
            filename = f"img_{timestamp}.png"
            path = ASSETS_DIR / filename
            
            # Ensure unique filename in case of collisions
            counter = 1
            while path.exists():
                filename = f"img_{timestamp}_{counter}.png"
                path = ASSETS_DIR / filename
                counter += 1
            
            path.write_bytes(response.content)
            print(f"GENERATE_IMAGE: Saved unique file: {filename}")
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    else:
        raise Exception("Failed to generate image with nano-banana")
    
    # CRITICAL: Set this generated image as the most recent for editing in thread-specific context
    thread_id = state.get("configurable", {}).get("thread_id", "default") if state else "default"
    if thread_id == "default":
        global _current_thread_id
        thread_id = _current_thread_id
    context = get_thread_context(thread_id)
    context['recent_path'] = str(path)
    # Also add to thread's uploaded images list for multi-image operations
    context['uploaded_images'].append(str(path))
    if len(context['uploaded_images']) > 5:
        context['uploaded_images'] = context['uploaded_images'][-5:]

    # Extract key subject from prompt for labeling (e.g., "cat", "dog", "cow")
    import re
    # Common animals and objects to look for in prompts
    subjects = ['cat', 'dog', 'cow', 'horse', 'bird', 'man', 'woman', 'person', 'car', 'tree', 'house', 'flower', 'mountain', 'ocean', 'sunset']
    prompt_lower = prompt.lower()
    found_subject = None
    for subject in subjects:
        if subject in prompt_lower:
            found_subject = subject
            break

    if found_subject:
        context['image_labels'][str(path)] = found_subject
        print(f"GENERATE_IMAGE: Labeled image as '{found_subject}'")

    print(f"GENERATE_IMAGE: Added to thread {thread_id} context: {path}")
    print(f"GENERATE_IMAGE: Thread now has {len(context['uploaded_images'])} images")
    
    filename = pathlib.Path(path).name
    return f'<img src="/assets/{filename}" class="message-image" alt="Generated image" onclick="openImageModal(\'/assets/{filename}\')"> Image generated with nano-banana: {prompt}. Saved to {path}'

# Thread-specific image storage to prevent cross-conversation contamination
_thread_image_context = {}  # {thread_id: {'recent_path': path, 'uploaded_images': [paths], 'image_labels': {}}}

def get_thread_context(thread_id):
    """Get or create thread-specific image context"""
    if thread_id not in _thread_image_context:
        _thread_image_context[thread_id] = {
            'recent_path': None,
            'uploaded_images': [],
            'image_labels': {}  # Map of path -> label (e.g., "cat", "dog", "cow")
        }
    return _thread_image_context[thread_id]

def set_recent_image_path(path, thread_id="default"):
    """Set recent image path for specific thread"""
    context = get_thread_context(thread_id)
    context['recent_path'] = path
    # Also add to uploaded images list (keep last 5 for multi-image generation)
    context['uploaded_images'].append(path)
    if len(context['uploaded_images']) > 5:
        context['uploaded_images'] = context['uploaded_images'][-5:]

def get_recent_image_paths(thread_id="default"):
    """Get list of recent image paths for specific thread"""
    context = get_thread_context(thread_id)
    return context['uploaded_images']

def clear_thread_context(thread_id):
    """Clear image context for a specific thread"""
    if thread_id in _thread_image_context:
        del _thread_image_context[thread_id]

# --- Tool: image editing (FAL AI nano-banana/edit) ------------------------
@tool
def edit_image(prompt: str, state: Annotated[dict, InjectedState], *, config: RunnableConfig) -> str:
    """
    Edit an existing image using FAL AI's nano-banana/edit model.
    Takes a prompt describing the desired changes.
    Uses the most recently uploaded image for editing.
    Returns HTML img tag for web display.
    """
    global _active_requests, _global_edit_lock, _thread_recent_edits, _langgraph_execution_tools

    # PROPER APPROACH: Read thread_id from RunnableConfig
    thread_id = config.get("configurable", {}).get("thread_id") if config else None

    # FAIL FAST: Don't guess or use fallbacks - require proper thread_id
    if not thread_id or thread_id == "default":
        # Only as a temporary compatibility measure, check global
        global _current_thread_id
        if _current_thread_id and _current_thread_id != "default":
            thread_id = _current_thread_id
            print(f"WARNING: edit_image using global thread_id fallback = {thread_id}")
        else:
            return "No active conversation context found. Please start a conversation or upload an image first."

    print(f"INFO: edit_image using thread_id = {thread_id}")
    context = get_thread_context(thread_id)
    recent_image_path = context['recent_path']
    print(f"DEBUG: edit_image recent_image_path = {recent_image_path}")
    print(f"DEBUG: edit_image thread context: {context}")
    
    # Define keys early to avoid NameError in exception handling
    current_time = time.time()
    
    # CLEAN PROMPT: Remove timestamp additions that web_app.py adds to make prompts unique
    clean_prompt = prompt
    if "Request timestamp:" in prompt:
        clean_prompt = prompt.split(" - Please be specific")[0]
    if "Please be specific about this exact edit" in prompt:
        clean_prompt = prompt.split(" - Please be specific")[0]
    
    prompt_hash = hash(clean_prompt)
    request_key = f"edit_{thread_id}_{prompt_hash}_{recent_image_path}"
    global_lock_key = f"{thread_id}_{prompt_hash}"
    execution_key = f"edit_image_{thread_id}_{prompt_hash}"  # Include prompt hash for bulk operations
    
    print(f"DEBUG: Original prompt: {prompt}")
    print(f"DEBUG: Cleaned prompt: {clean_prompt}")
    print(f"DEBUG: Prompt hash: {prompt_hash}")
    
    try:
        # ENHANCED DUPLICATE PREVENTION: Check both local and global locks
        
        # ADDITIONAL CHECK: Look for similar recent requests on the same image
        image_lock_key = f"{thread_id}_{recent_image_path}"
        similar_request_found = False
        
        # Check if ANY edit request on this image+thread happened recently (within 30 seconds)
        for key, timestamp in _global_edit_lock.items():
            if key.startswith(f"{thread_id}_") and (current_time - timestamp) < 30:
                # This is a recent request on the same thread
                print(f"SIMILAR REQUEST CHECK: Found recent request {key} from {current_time - timestamp:.1f}s ago")
                similar_request_found = True
                break
        
        # REMOVED: Old 60-second bulletproof block that prevented bulk operations
        # Now allowing multiple edits with different prompts for bulk operations like "5 different styles"

        # LANGGRAPH EXECUTION TRACKING: Prevent coordinator from calling edit_image twice
        if execution_key in _langgraph_execution_tools:
            last_call_time = _langgraph_execution_tools[execution_key]
            if (current_time - last_call_time) < 10:  # Within 10 seconds - likely same LangGraph execution
                print(f"LANGGRAPH DUPLICATE CHECK: edit_image already called in this execution {current_time - last_call_time:.1f}s ago")
                return f"Edit operation already attempted in this conversation turn. Please try a new request or refresh the page."
        
        # Check if this exact request is already in progress (within last 15 seconds)
        if request_key in _active_requests or global_lock_key in _global_edit_lock or similar_request_found:
            if request_key in _active_requests:
                time_diff = current_time - _active_requests[request_key]
                reason = "exact request"
            elif global_lock_key in _global_edit_lock:
                time_diff = current_time - _global_edit_lock[global_lock_key]
                reason = "same prompt"
            else:
                time_diff = 30  # Default for similar request
                reason = "similar recent request"
            
            if time_diff < 30:  # Block duplicates within 30 seconds (extended for similar requests)
                print(f"DUPLICATE BLOCKED: Edit request blocked ({reason}, last request {time_diff:.1f}s ago)")
                return f"Edit request already processed recently for this image. Please wait..."
        
        # Clean up old requests (older than 5 minutes)
        _active_requests = {k: v for k, v in _active_requests.items() if current_time - v < 300}
        _global_edit_lock = {k: v for k, v in _global_edit_lock.items() if current_time - v < 300}
        _thread_recent_edits = {k: v for k, v in _thread_recent_edits.items() if current_time - v < 300}
        _langgraph_execution_tools = {k: v for k, v in _langgraph_execution_tools.items() if current_time - v < 300}
        
        # Mark request as active in both systems
        _active_requests[request_key] = current_time
        _global_edit_lock[global_lock_key] = current_time
        _thread_recent_edits[thread_id] = current_time  # Track recent edit for this thread
        _langgraph_execution_tools[execution_key] = current_time  # Track LangGraph execution
        print(f"EDIT REQUEST: Started with key {request_key} and global lock {global_lock_key}")
        # Use the thread-specific recent image path
        if recent_image_path is None:
            return "No image available to edit. Please upload an image first."
        
        image_path = recent_image_path
        
        # Check if file exists before proceeding
        if not image_path.startswith(('http://', 'https://')):
            if not os.path.exists(image_path):
                return f"Image file not found: {image_path}. Please upload a new image to edit."
        
        # Upload the image file to FAL
        if image_path.startswith(('http://', 'https://')):
            fal_image_url = image_path
        else:
            # Upload local file to FAL
            fal_image_url = fal_client.upload_file(image_path)
        
        result = fal_client.subscribe(
            "fal-ai/nano-banana/edit",
            arguments={
                "prompt": clean_prompt,
                "image_urls": [fal_image_url],
                "num_images": 1
            },
            with_logs=True
        )
        
        if result and result.get('images') and len(result['images']) > 0:
            edited_image_url = result['images'][0]['url']
            
            # Download and save the edited image locally
            import requests
            response = requests.get(edited_image_url)
            if response.status_code == 200:
                # Use microsecond precision to avoid filename collisions in bulk operations
                import time as time_module
                timestamp = int(time_module.time() * 1000000)  # Microsecond timestamp
                edited_path = ASSETS_DIR / f"edited_{timestamp}.png"

                # Ensure unique filename in case of collisions
                counter = 1
                while edited_path.exists():
                    timestamp = int(time_module.time() * 1000000)
                    edited_path = ASSETS_DIR / f"edited_{timestamp}_{counter}.png"
                    counter += 1

                edited_path.write_bytes(response.content)
                filename = edited_path.name
                
                # CRITICAL FIX: Update the recent_path context to use the edited image for future operations
                context['recent_path'] = str(edited_path)
                # Also add the edited image to the uploaded images list for multi-image operations
                context['uploaded_images'].append(str(edited_path))
                if len(context['uploaded_images']) > 5:
                    context['uploaded_images'] = context['uploaded_images'][-5:]
                print(f"EDIT_IMAGE: Added to thread {thread_id} context: {edited_path}")
                print(f"EDIT_IMAGE: Thread now has {len(context['uploaded_images'])} images")
                
                # Clean up active request
                if request_key in _active_requests:
                    del _active_requests[request_key]
                
                return f'<img src="/assets/{filename}" class="message-image" alt="Edited image" onclick="openImageModal(\'/assets/{filename}\')"> Image edited with nano-banana: {clean_prompt}\nSaved as {edited_path}\nTimestamp: {int(time.time())}'
            else:
                # Clean up active request on failure
                if request_key in _active_requests:
                    del _active_requests[request_key]
                return "Failed to download edited image"
        else:
            # Clean up active request on failure
            if request_key in _active_requests:
                del _active_requests[request_key]
            return "Failed to edit image"
            
    except Exception as e:
        # Clean up active request and global lock on error
        if request_key in _active_requests:
            del _active_requests[request_key]
        if global_lock_key in _global_edit_lock:
            del _global_edit_lock[global_lock_key]
        print(f"EDIT REQUEST: Failed with error: {str(e)}")
        print(f"EDIT REQUEST: Error type: {type(e).__name__}")
        print(f"EDIT REQUEST: Cleaned up key {request_key} and global lock {global_lock_key}")
        import traceback
        print(f"EDIT REQUEST: Full traceback: {traceback.format_exc()}")
        return f"Error editing image: {str(e)}"

# --- Tool: text-to-video generation (FAL AI LTX-Video) --------------------
@tool
def generate_video_from_text(prompt: str, 
                            resolution: str = "720p",
                            aspect_ratio: str = "16:9",
                            num_frames: int = 121,
                            frame_rate: int = 30) -> str:
    """
    Generate a video from a text prompt using FAL AI's LTX-Video-13B model.
    Creates high-quality videos from detailed text descriptions.
    Returns HTML video tag for web display.
    """
    global _active_requests
    
    print(f"DEBUG: generate_video_from_text called with prompt: {prompt}")
    
    try:
        # Create request key to prevent duplicates
        request_key = f"video_text_{hash(prompt)}_{resolution}"
        
        # Check if this exact request is already in progress
        if request_key in _active_requests:
            return f"Video generation already in progress for this prompt. Please wait..."
        
        # Clean up old requests and mark as active
        current_time = time.time()
        _active_requests = {k: v for k, v in _active_requests.items() if current_time - v < 300}
        _active_requests[request_key] = current_time
        result = fal_client.subscribe(
            "fal-ai/ltx-video",
            arguments={
                "prompt": prompt,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "negative_prompt": "worst quality, inconsistent motion, blurry, jittery, distorted"
            },
            with_logs=True
        )
        
        # Check for video URL in result (FAL AI may return different structures)
        video_url = None
        if result:
            if isinstance(result, dict):
                # Try different possible response structures
                if 'video' in result and result['video']:
                    if isinstance(result['video'], dict) and 'url' in result['video']:
                        video_url = result['video']['url']
                    elif isinstance(result['video'], str):
                        video_url = result['video']
                elif 'url' in result:
                    video_url = result['url']
                elif 'output' in result:
                    video_url = result['output']

        if video_url:
            
            # Download and save the video locally
            try:
                local_video_path = save_video_from_url(video_url)
                filename = pathlib.Path(local_video_path).name
                
                # Clean up active request
                if request_key in _active_requests:
                    del _active_requests[request_key]
                
                # Return HTML video element for web display
                return f'<video controls class="message-video" style="max-width: 500px; border-radius: 12px; margin: 12px 0;"><source src="/videos/{filename}" type="video/mp4">Your browser does not support the video tag.</video>Successfully generated video: {prompt}\nVideo saved to {local_video_path}'
            except Exception as download_error:
                # Clean up active request
                if request_key in _active_requests:
                    del _active_requests[request_key]
                # Fallback: use the direct URL if download fails
                return f'<video controls class="message-video" style="max-width: 500px; border-radius: 12px; margin: 12px 0;"><source src="{video_url}" type="video/mp4">Your browser does not support the video tag.</video>Video generated: {video_url}'
        else:
            # Clean up active request on failure
            if request_key in _active_requests:
                del _active_requests[request_key]
            return "Failed to generate video from text prompt"
            
    except Exception as e:
        # Clean up active request on error
        if 'request_key' in locals() and request_key in _active_requests:
            del _active_requests[request_key]
        print(f"ERROR in generate_video_from_text: {str(e)}")
        print(f"Full error details: {type(e).__name__}: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return f"Error generating video: {str(e)}. The FAL AI video generation service might be temporarily unavailable or the API key might need to be verified."

# --- Tool: image-to-video generation (FAL AI LTX-Video) -------------------
@tool
def generate_video_from_image(prompt: str,
                             resolution: str = "720p",
                             aspect_ratio: str = "auto",
                             num_frames: int = 121,
                             frame_rate: int = 30,
                             state: Annotated[dict, InjectedState] = None,
                             *,
                             config: RunnableConfig = None) -> str:
    """
    Generate a video from an existing image and text prompt using FAL AI's LTX-Video-13B model.
    Intelligently selects the appropriate image based on the prompt content.
    Returns HTML video tag for web display.
    """
    # PROPER APPROACH: Read thread_id from RunnableConfig (not from state or globals)
    thread_id = config.get("configurable", {}).get("thread_id") if config else None

    # FAIL FAST: Don't guess or use fallbacks - require proper thread_id
    if not thread_id or thread_id == "default":
        # Only as a temporary compatibility measure, check global
        global _current_thread_id
        if _current_thread_id and _current_thread_id != "default":
            thread_id = _current_thread_id
            print(f"WARNING: generate_video_from_image using global thread_id fallback = {thread_id}")
        else:
            raise RuntimeError(
                "Missing thread_id in config. This indicates a config propagation issue. "
                "Please ensure RunnableConfig is passed through all node invocations."
            )

    print(f"INFO: generate_video_from_image using thread_id = {thread_id}")

    context = get_thread_context(thread_id)

    # FALLBACK: If context is empty, try to recover from message history
    if not context['uploaded_images'] and state and 'messages' in state:
        messages = state.get('messages', [])
        print(f"DEBUG: Context empty, checking {len(messages)} messages for images")
        for msg in messages[-10:]:  # Check last 10 messages
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                import re
                pattern = r'/(?:app/data/)?assets/img_\d+\.png'
                found_paths = re.findall(pattern, msg.content)
                for path in found_paths:
                    # Normalize path
                    if not path.startswith('/app/data'):
                        if path.startswith('/assets'):
                            path = f"/app/data{path}"
                        else:
                            path = f"/app/data/assets/{os.path.basename(path)}"

                    if os.path.exists(path) and path not in context['uploaded_images']:
                        context['uploaded_images'].append(path)
                        # Extract label from message
                        label_patterns = ['cat', 'dog', 'cow', 'horse', 'bird', 'man', 'woman']
                        for label in label_patterns:
                            if label in msg.content.lower():
                                context.setdefault('image_labels', {})[path] = label
                                print(f"FALLBACK: Found {label} image at {path}")
                                break

        if context['uploaded_images'] and not context['recent_path']:
            context['recent_path'] = context['uploaded_images'][-1]

    # Smart image selection based on prompt content
    image_path = None
    prompt_lower = prompt.lower()

    # First, try to find an image that matches a subject in the prompt
    image_labels = context.get('image_labels', {})
    if image_labels:
        print(f"DEBUG: Available image labels: {image_labels}")
        for path, label in image_labels.items():
            if label.lower() in prompt_lower:
                if os.path.exists(path):
                    image_path = path
                    print(f"DEBUG: Selected image with label '{label}' matching prompt")
                    break

    # If no matching label found, use the most recent image
    if not image_path:
        image_path = context['recent_path']
        print(f"DEBUG: No matching label found, using recent image: {image_path}")
    
    try:
        # Check if we have a valid image path
        if image_path is None:
            return "No image available for video generation. Please upload an image first."
        
        # Check if file exists before proceeding
        if not image_path.startswith(('http://', 'https://')):
            if not os.path.exists(image_path):
                return f"Image file not found: {image_path}. Please upload a new image for video generation."
        
        # Upload the image file to FAL if it's local
        if image_path.startswith(('http://', 'https://')):
            fal_image_url = image_path
        else:
            # Upload local file to FAL
            fal_image_url = fal_client.upload_file(image_path)
        
        result = fal_client.subscribe(
            "fal-ai/ltx-video-13b-distilled/image-to-video",
            arguments={
                "prompt": prompt,
                "image_url": fal_image_url,
                "negative_prompt": "worst quality, inconsistent motion, blurry, jittery, distorted",
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
                "num_frames": num_frames,
                "frame_rate": frame_rate,
                "enable_safety_checker": True,
                "expand_prompt": True,
                "constant_rate_factor": 35
            },
            with_logs=True
        )
        
        # Check for video URL in result (FAL AI may return different structures)
        video_url = None
        if result:
            if isinstance(result, dict):
                # Try different possible response structures
                if 'video' in result and result['video']:
                    if isinstance(result['video'], dict) and 'url' in result['video']:
                        video_url = result['video']['url']
                    elif isinstance(result['video'], str):
                        video_url = result['video']
                elif 'url' in result:
                    video_url = result['url']
                elif 'output' in result:
                    video_url = result['output']

        if video_url:
            
            # Download and save the video locally
            try:
                local_video_path = save_video_from_url(video_url)
                filename = pathlib.Path(local_video_path).name
                
                # Return HTML video element for web display
                return f'<video controls class="message-video" style="max-width: 500px; border-radius: 12px; margin: 12px 0;"><source src="/videos/{filename}" type="video/mp4">Your browser does not support the video tag.</video>Video saved to {local_video_path}'
            except Exception as download_error:
                # Fallback: use the direct URL if download fails
                return f'<video controls class="message-video" style="max-width: 500px; border-radius: 12px; margin: 12px 0;"><source src="{video_url}" type="video/mp4">Your browser does not support the video tag.</video>Video generated: {video_url}'
        else:
            return "Failed to generate video from image"
            
    except Exception as e:
        return f"Error generating video from image: {str(e)}"

# --- Tool: multi-image generation (FAL AI nano-banana/edit) ---------------
# Global tracker for multi-image requests to prevent duplicates
_multi_image_active = False

@tool
def generate_image_from_multiple(prompt: str,
                                num_images: int = 1,
                                state: Annotated[dict, InjectedState] = None,
                                *,
                                config: RunnableConfig = None) -> str:
    """
    Generate a new image using multiple previously uploaded images as context.
    Combines elements from 2 or more uploaded images based on the text prompt using nano-banana/edit.
    Requires at least 2 images to have been uploaded in the current session.
    Returns HTML img tag for web display.
    """
    # DUPLICATE PREVENTION: Check if already processing
    global _multi_image_active
    if _multi_image_active:
        return "Multi-image generation is already in progress. Please wait for the current request to complete."

    try:
        _multi_image_active = True

        # PROPER APPROACH: Read thread_id from RunnableConfig
        thread_id = config.get("configurable", {}).get("thread_id") if config else None

        # FAIL FAST: Don't guess or use fallbacks - require proper thread_id
        if not thread_id or thread_id == "default":
            # Only as a temporary compatibility measure, check global
            global _current_thread_id
            if _current_thread_id and _current_thread_id != "default":
                thread_id = _current_thread_id
                print(f"WARNING: generate_image_from_multiple using global thread_id fallback = {thread_id}")
            else:
                _multi_image_active = False
                raise RuntimeError(
                    "Missing thread_id in config. This indicates a config propagation issue. "
                    "Please ensure RunnableConfig is passed through all node invocations."
                )

        print(f"INFO: generate_image_from_multiple using thread_id = {thread_id}")
        context = get_thread_context(thread_id)
        uploaded_images = context['uploaded_images']
        
        print(f"CRITICAL DEBUG: generate_image_from_multiple called!")
        print(f"CRITICAL DEBUG: thread_id = {thread_id}")
        print(f"CRITICAL DEBUG: uploaded_images = {uploaded_images}")
        print(f"CRITICAL DEBUG: prompt = {prompt}")
    
        # ENHANCED CHECK: Filter out very old or potentially contaminated images
        import time
        current_time = int(time.time())
        
        # Filter images to only recent ones (within last 10 minutes = 600 seconds)
        recent_images = []
        for img_path in uploaded_images:
            # FIXED: Include ALL uploaded images, not just those with specific patterns
            # Check if it's an uploaded image (either generated or user-uploaded)
            if 'uploads/' in img_path or 'assets/' in img_path or 'img_' in img_path or 'multi_' in img_path or 'edited_' in img_path:
                try:
                    # Extract timestamp from filename
                    import re
                    timestamp_match = re.search(r'(\d{10,})', img_path)
                    if timestamp_match:
                        img_timestamp = int(timestamp_match.group(1))
                        # Only include images from last 10 minutes
                        if current_time - img_timestamp < 600:
                            recent_images.append(img_path)
                        else:
                            print(f"DEBUG: Filtering out old image: {img_path} (timestamp: {img_timestamp})")
                    else:
                        # If no timestamp found, assume it's recent (for user-uploaded files)
                        recent_images.append(img_path)
                        print(f"DEBUG: Including image without timestamp (assumed recent): {img_path}")
                except:
                    # If any error in processing, include the image
                    recent_images.append(img_path)
            else:
                # FALLBACK: If image doesn't match any pattern, still include it
                recent_images.append(img_path)
                print(f"DEBUG: Including image (no pattern match but keeping): {img_path}")
        
        print(f"DEBUG: Filtered from {len(uploaded_images)} to {len(recent_images)} recent images")
        uploaded_images = recent_images
        
        # Check if we need to look deeper for images from conversation history
        if len(uploaded_images) < 2:
            print(f"DEBUG: Only {len(uploaded_images)} recent images in thread context")
            # If we have exactly 1 image and it's a recent generation, this might be a follow-up request
            if len(uploaded_images) == 1:
                _multi_image_active = False
                return f"Only 1 recent image available in current conversation. For multi-image fusion, please generate or upload more images first, or try a different operation on the single image."
            else:
                _multi_image_active = False
                return f"No recent images available for multi-image generation. Please generate or upload images first, then try combining them."
        
        # Final check if we have enough images in this thread after filtering
        if len(uploaded_images) < 2:
            _multi_image_active = False
            return f"Multi-image generation requires at least 2 uploaded images. Currently have {len(uploaded_images)} image(s). Please upload more images first."
        
        # Use the most recent images (up to 5) from this thread only
        images_to_use = uploaded_images[-min(5, len(uploaded_images)):]
        
        # Upload all images to FAL for processing
        fal_image_urls = []
        for image_path in images_to_use:
            try:
                if image_path.startswith(('http://', 'https://')):
                    fal_image_urls.append(image_path)
                else:
                    # Check if file exists
                    if not os.path.exists(image_path):
                        continue  # Skip missing files
                    # Upload to FAL
                    fal_url = fal_client.upload_file(image_path)
                    fal_image_urls.append(fal_url)
            except Exception as upload_error:
                print(f"Warning: Failed to upload {image_path}: {upload_error}")
                continue
        
        if len(fal_image_urls) < 2:
            return "Unable to process enough images for multi-image generation. Please ensure uploaded images are accessible."
        
        # Call FAL AI nano-banana/edit API
        result = fal_client.subscribe(
            "fal-ai/nano-banana/edit",
            arguments={
                "prompt": prompt,
                "image_urls": fal_image_urls,
                "num_images": num_images
            },
            with_logs=True
        )
        
        if result and result.get('images') and len(result['images']) > 0:
            # Get the first generated image
            image_info = result['images'][0]
            image_url = image_info.get('url')
            
            if image_url:
                # Download and save the image locally
                try:
                    import requests
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        # Save with multi_ prefix to distinguish from single image generation
                        timestamp = int(time.time())
                        filename = f"multi_{timestamp}.png"
                        local_path = ASSETS_DIR / filename
                        local_path.write_bytes(response.content)
                        
                        # Update thread-specific recent image path for potential further editing
                        context['recent_path'] = str(local_path)
                        
                        # Reset the active flag
                        _multi_image_active = False
                        
                        return f'<img src="/assets/{filename}" class="message-image" alt="Multi-image generated" onclick="openImageModal(\'/assets/{filename}\')"> Multi-image created with nano-banana from {len(fal_image_urls)} images, saved to {local_path}'
                    else:
                        # Reset the active flag
                        _multi_image_active = False
                        # Fallback: use the direct URL
                        return f'<img src="{image_url}" class="message-image" alt="Multi-image generated"> Multi-image generated with nano-banana from {len(fal_image_urls)} source images'
                except Exception as download_error:
                    # Reset the active flag
                    _multi_image_active = False
                    # Fallback: use the direct URL
                    return f'<img src="{image_url}" class="message-image" alt="Multi-image generated"> Multi-image generated with nano-banana from {len(fal_image_urls)} source images'
            else:
                _multi_image_active = False
                return "Failed to generate multi-image: No image URL in response"
        else:
            _multi_image_active = False
            return "Failed to generate multi-image: Invalid response from API"
            
    except Exception as e:
        _multi_image_active = False
        return f"Error generating multi-image: {str(e)}"

# Global state for multi-step task tracking and request deduplication
_multi_step_context = {}
_active_requests = {}  # Track active FAL AI requests to prevent duplicates
_current_thread_id = "default"  # Track the current thread ID for tools
_global_edit_lock = {}  # Global edit operation lock to prevent cross-endpoint duplicates
_thread_recent_edits = {}  # Track recent edit operations by thread to prevent UI double-calls
_langgraph_execution_tools = {}  # Track tool calls within single LangGraph execution

@tool
def evaluate_result_quality(user_request: str, operation_type: str, result_content: str) -> str:
    """
    Evaluate if the generated result meets the user's expectations and request.
    Returns evaluation and suggestions for improvement if needed.
    """
    try:
        from langchain_openai import ChatOpenAI
        
        # Use a smaller model for quick evaluation
        evaluator_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        evaluation_prompt = f"""
        Evaluate if this result meets the user's request:
        
        USER REQUEST: {user_request}
        OPERATION TYPE: {operation_type}
        RESULT: {result_content}
        
        Check:
        1. Does the response match what the user asked for?
        2. Is the operation type correct for the request?
        3. Are there any obvious mismatches?
        
        Respond with:
        - "VALID" if the result matches the request
        - "INVALID: [reason]" if there's a mismatch
        - "RETRY: [specific instruction]" if the operation should be retried
        """
        
        evaluation = evaluator_model.invoke([{"role": "user", "content": evaluation_prompt}])
        return evaluation.content
        
    except Exception as e:
        return f"VALID (evaluation unavailable: {str(e)})"

@tool
def check_image_context(state: Annotated[dict, InjectedState], *, config: RunnableConfig) -> str:
    """
    Check what images are available for editing or animation.
    Returns information about available images and uploaded image count.
    """
    # PROPER APPROACH: Read thread_id from RunnableConfig (not from state or globals)
    thread_id = config.get("configurable", {}).get("thread_id") if config else None

    # FAIL FAST: Don't guess or use fallbacks - require proper thread_id
    if not thread_id or thread_id == "default":
        # Only as a temporary compatibility measure, check global
        global _current_thread_id
        if _current_thread_id and _current_thread_id != "default":
            thread_id = _current_thread_id
            print(f"WARNING: check_image_context using global thread_id fallback = {thread_id}")
        else:
            raise RuntimeError(
                "Missing thread_id in config. This indicates a config propagation issue. "
                "Please ensure RunnableConfig is passed through all node invocations."
            )

    print(f"INFO: check_image_context using thread_id = {thread_id}")

    context = get_thread_context(thread_id)
    recent_image_path = context['recent_path']
    uploaded_images = context['uploaded_images']

    # FALLBACK: If no images in context, check recent messages for generated images
    if not uploaded_images and state and 'messages' in state:
        messages = state.get('messages', [])
        for msg in messages[-10:]:  # Check last 10 messages
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                # Look for image paths in message content
                import re
                # Pattern to find saved image paths
                pattern = r'/(?:app/data/)?assets/img_\d+\.png'
                found_paths = re.findall(pattern, msg.content)
                for path in found_paths:
                    # Normalize path
                    if not path.startswith('/app/data'):
                        if path.startswith('/assets'):
                            path = f"/app/data{path}"
                        else:
                            path = f"/app/data/assets/{os.path.basename(path)}"

                    if os.path.exists(path) and path not in uploaded_images:
                        uploaded_images.append(path)
                        context['uploaded_images'].append(path)

                        # Try to extract label from the message
                        label_patterns = ['cat', 'dog', 'cow', 'horse', 'bird', 'man', 'woman']
                        for label in label_patterns:
                            if label in msg.content.lower():
                                context.setdefault('image_labels', {})[path] = label
                                break

        if uploaded_images:
            print(f"FALLBACK: Found {len(uploaded_images)} images in message history")
            # Set the most recent as the recent_path
            if not recent_image_path and uploaded_images:
                context['recent_path'] = uploaded_images[-1]
                recent_image_path = uploaded_images[-1]

    print(f"DEBUG: check_image_context for thread {thread_id}")
    print(f"DEBUG: recent_image_path = {recent_image_path}")
    print(f"DEBUG: uploaded_images = {uploaded_images}")
    print(f"DEBUG: All thread contexts: {list(_thread_image_context.keys())}")
    
    context_info = []

    # Check recent image for editing
    if recent_image_path and os.path.exists(recent_image_path):
        label = context.get('image_labels', {}).get(recent_image_path, 'unknown')
        context_info.append(f"✅ Recent image available: {label} - {recent_image_path}")
    else:
        context_info.append("❌ No recent image available")

    # Check all available images with their labels
    valid_uploads = [img for img in uploaded_images if os.path.exists(img)]
    if valid_uploads:
        context_info.append(f"✅ {len(valid_uploads)} images available:")
        for img_path in valid_uploads:
            label = context.get('image_labels', {}).get(img_path, 'unlabeled')
            context_info.append(f"   - {label}: {os.path.basename(img_path)}")
    else:
        context_info.append("❌ No images available in context")

    # Add specific guidance
    if valid_uploads:
        context_info.append("\n📌 You can:")
        context_info.append("- Use generate_video_from_image to animate any of these images")
        context_info.append("- Use edit_image to modify the recent image")
        if len(valid_uploads) >= 2:
            context_info.append("- Use generate_image_from_multiple to combine images")

    return "\n".join(context_info)

# === PDF CONVERSION TOOLS ===================================================

# --- Tool: PDF to Images Conversion ------------------------------------------
@tool
def convert_pdf_to_images(file_path: str, output_format: str = "png", *, config: RunnableConfig) -> str:
    """
    Convert PDF pages to individual image files (PNG or JPG).
    Each page becomes a separate image file.

    IMPORTANT: When user asks for JPG/JPEG output, specify output_format='jpg'

    Args:
        file_path: Path to the PDF file
        output_format: Output format - use 'png' or 'jpg' (default: 'png')
                      Examples: output_format='jpg' for JPEG output

    Returns:
        HTML with downloadable image links
    """
    try:
        print(f"INFO: Converting PDF to {output_format} images: {file_path}")

        # Validate file exists
        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Convert PDF to images
        image_paths = pdf_converter.pdf_to_images(file_path, output_format=output_format)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        html_parts = []

        for i, img_path in enumerate(image_paths, 1):
            filename = os.path.basename(img_path)
            html_parts.append(
                f'<img src="/assets/{filename}" class="message-image" alt="Page {i}" '
                f'onclick="openImageModal(\'/assets/{filename}\')" style="max-width: 150px; margin: 5px;">'
            )

        return "".join(html_parts)

    except Exception as e:
        return f"❌ Error converting PDF to images: {str(e)}"

# --- Tool: PDF to Word Conversion --------------------------------------------
@tool
def convert_pdf_to_word(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PDF document to Word (DOCX) format.
    Extracts text and preserves basic formatting.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename

    Returns:
        HTML with download link for the generated Word document
    """
    try:
        print(f"INFO: Converting PDF to Word: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info first
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Convert PDF to Word
        docx_path = pdf_converter.pdf_to_word(file_path, output_name=output_name)
        filename = os.path.basename(docx_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PDF to Word: {str(e)}"

# --- Tool: PDF to Excel Conversion -------------------------------------------
@tool
def convert_pdf_to_excel(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PDF document to Excel (XLSX) format.
    Extracts text and table data.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename

    Returns:
        HTML with download link for the generated Excel file
    """
    try:
        print(f"INFO: Converting PDF to Excel: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Convert PDF to Excel
        xlsx_path = pdf_converter.pdf_to_excel(file_path, output_name=output_name)
        filename = os.path.basename(xlsx_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PDF to Excel: {str(e)}"

# --- Tool: PDF to PowerPoint Conversion --------------------------------------
@tool
def convert_pdf_to_powerpoint(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PDF document to PowerPoint (PPTX) format.
    Each PDF page becomes a slide with an image.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename

    Returns:
        HTML with download link for the generated PowerPoint file
    """
    try:
        print(f"INFO: Converting PDF to PowerPoint: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Convert PDF to PowerPoint
        pptx_path = pdf_converter.pdf_to_powerpoint(file_path, output_name=output_name)
        filename = os.path.basename(pptx_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PDF to PowerPoint: {str(e)}"

# === EXTENDED FORMAT CONVERSION TOOLS ========================================

# --- Tool: Excel to CSV Conversion -------------------------------------------
@tool
def convert_excel_to_csv(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Excel spreadsheet (XLSX/XLS) to CSV format using LibreOffice.
    Exports the first sheet as comma-separated values.

    Args:
        file_path: Path to the Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted CSV file
    """
    try:
        print(f"INFO: Converting Excel to CSV: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Excel file not found at {file_path}"

        csv_path = pdf_converter.excel_to_csv(file_path, output_name)
        filename = os.path.basename(csv_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Excel to CSV: {str(e)}"

# --- Tool: CSV to Excel Conversion -------------------------------------------
@tool
def convert_csv_to_excel(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert CSV file to Excel spreadsheet (XLSX) format using LibreOffice.
    Creates a properly formatted Excel workbook from CSV data.

    Args:
        file_path: Path to the CSV file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted Excel file
    """
    try:
        print(f"INFO: Converting CSV to Excel: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: CSV file not found at {file_path}"

        xlsx_path = pdf_converter.csv_to_excel(file_path, output_name)
        filename = os.path.basename(xlsx_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting CSV to Excel: {str(e)}"

# --- Tool: Word to TXT Conversion --------------------------------------------
@tool
def convert_word_to_txt(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Word document (DOCX/DOC) to plain text (TXT) format using LibreOffice.
    Extracts all text content without formatting.

    Args:
        file_path: Path to the Word file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted TXT file
    """
    try:
        print(f"INFO: Converting Word to TXT: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Word file not found at {file_path}"

        txt_path = pdf_converter.word_to_txt(file_path, output_name)
        filename = os.path.basename(txt_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Word to TXT: {str(e)}"

# --- Tool: Excel to TXT Conversion -------------------------------------------
@tool
def convert_excel_to_txt(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Excel spreadsheet (XLSX/XLS) to plain text (TXT) format using LibreOffice.
    Exports spreadsheet data as tab-separated plain text.

    Args:
        file_path: Path to the Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted TXT file
    """
    try:
        print(f"INFO: Converting Excel to TXT: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Excel file not found at {file_path}"

        txt_path = pdf_converter.excel_to_txt(file_path, output_name)
        filename = os.path.basename(txt_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Excel to TXT: {str(e)}"

# --- Tool: Word to HTML Conversion -------------------------------------------
@tool
def convert_word_to_html(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Word document (DOCX/DOC) to HTML format using LibreOffice.
    Preserves formatting, tables, and structure in web format.

    Args:
        file_path: Path to the Word file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted HTML file
    """
    try:
        print(f"INFO: Converting Word to HTML: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Word file not found at {file_path}"

        html_path = pdf_converter.word_to_html(file_path, output_name)
        filename = os.path.basename(html_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Word to HTML: {str(e)}"

# --- Tool: Excel to HTML Conversion ------------------------------------------
@tool
def convert_excel_to_html(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Excel spreadsheet (XLSX/XLS) to HTML format using LibreOffice.
    Creates an HTML table from spreadsheet data with formatting preserved.

    Args:
        file_path: Path to the Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted HTML file
    """
    try:
        print(f"INFO: Converting Excel to HTML: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Excel file not found at {file_path}"

        html_path = pdf_converter.excel_to_html(file_path, output_name)
        filename = os.path.basename(html_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Excel to HTML: {str(e)}"

# --- Tool: PowerPoint to HTML Conversion -------------------------------------
@tool
def convert_powerpoint_to_html(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PowerPoint presentation (PPTX/PPT) to HTML format using LibreOffice.
    Creates a web-viewable version of the presentation.

    Args:
        file_path: Path to the PowerPoint file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted HTML file
    """
    try:
        print(f"INFO: Converting PowerPoint to HTML: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PowerPoint file not found at {file_path}"

        html_path = pdf_converter.powerpoint_to_html(file_path, output_name)
        filename = os.path.basename(html_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PowerPoint to HTML: {str(e)}"

# === END EXTENDED FORMAT CONVERSIONS =========================================

# --- Tool: Word to PDF Conversion --------------------------------------------
@tool
def convert_word_to_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Word document (DOCX/DOC) to PDF format using LibreOffice.

    Args:
        file_path: Path to the Word file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted PDF
    """
    try:
        print(f"INFO: Converting Word to PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Word file not found at {file_path}"

        pdf_path = pdf_converter.word_to_pdf(file_path, output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Word to PDF: {str(e)}"

# --- Tool: Excel to PDF Conversion -------------------------------------------
@tool
def convert_excel_to_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert Excel spreadsheet (XLSX/XLS) to PDF format using LibreOffice.

    Args:
        file_path: Path to the Excel file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted PDF
    """
    try:
        print(f"INFO: Converting Excel to PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Excel file not found at {file_path}"

        pdf_path = pdf_converter.excel_to_pdf(file_path, output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting Excel to PDF: {str(e)}"

# --- Tool: PowerPoint to PDF Conversion --------------------------------------
@tool
def convert_powerpoint_to_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PowerPoint presentation (PPTX/PPT) to PDF format using LibreOffice.

    Args:
        file_path: Path to the PowerPoint file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted PDF
    """
    try:
        print(f"INFO: Converting PowerPoint to PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PowerPoint file not found at {file_path}"

        pdf_path = pdf_converter.powerpoint_to_pdf(file_path, output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PowerPoint to PDF: {str(e)}"

# --- Tool: Images to PDF Conversion ------------------------------------------
@tool
def convert_images_to_pdf(output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Combine multiple uploaded images into a single PDF document.
    Uses the most recently uploaded images from the current conversation.

    Args:
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the combined PDF
    """
    try:
        print(f"INFO: Converting images to PDF")

        # Get thread_id from config
        thread_id = config.get("configurable", {}).get("thread_id", "default")

        # Get recent image paths from conversation context
        image_paths = get_recent_image_paths(thread_id)

        if not image_paths or len(image_paths) == 0:
            return "❌ Error: No images found. Please upload images first before converting to PDF."

        print(f"INFO: Found {len(image_paths)} images for thread {thread_id}: {image_paths}")

        # Verify all images exist
        valid_paths = []
        for path in image_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                print(f"WARNING: Image not found: {path}")

        if len(valid_paths) == 0:
            return "❌ Error: None of the uploaded images could be found. Please upload images again."

        # Convert images to PDF
        pdf_path = pdf_converter.images_to_pdf(valid_paths, output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting images to PDF: {str(e)}"

# --- Tool: Convert Image File to PDF ----------------------------------------
@tool
def convert_image_file_to_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert a single image file (PNG, JPG, JPEG, GIF, WEBP) to PDF format.
    Use this for image files that were uploaded as documents.

    Args:
        file_path: Path to the image file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for converted PDF
    """
    try:
        print(f"INFO: Converting image file to PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Image file not found at {file_path}"

        # Check if it's an image file
        ext = file_path.lower().split('.')[-1]
        if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            return f"❌ Error: File is not an image. Extension: {ext}"

        # Convert single image to PDF
        pdf_path = pdf_converter.images_to_pdf([file_path], output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting image to PDF: {str(e)}"

# --- Tool: Merge PDFs --------------------------------------------------------
@tool
def merge_pdfs(file_paths: List[str], output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Merge multiple PDF files into a single PDF document.
    Use this when the user uploads multiple PDFs and wants to combine them.

    Args:
        file_paths: List of PDF file paths to merge (must be absolute paths)
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the merged PDF
    """
    try:
        if not file_paths or len(file_paths) == 0:
            return "❌ Error: No PDF files provided for merging."

        if len(file_paths) == 1:
            return "❌ Error: Need at least 2 PDF files to merge. Only 1 PDF provided."

        print(f"INFO: Merging {len(file_paths)} PDF files")

        # Validate all paths exist
        valid_paths = []
        for path in file_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                print(f"WARNING: PDF not found: {path}")

        if len(valid_paths) == 0:
            return "❌ Error: None of the PDF files could be found."

        if len(valid_paths) == 1:
            return f"❌ Error: Only 1 valid PDF found. Need at least 2 PDFs to merge."

        # Merge PDFs
        merged_path = pdf_converter.merge_pdfs(valid_paths, output_name)
        filename = os.path.basename(merged_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error merging PDFs: {str(e)}"

# --- Tool: Extract Text from PDF --------------------------------------------
@tool
def extract_text_from_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Extract all text from a PDF document to a plain text file.
    Useful for converting PDF text to editable format.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated text file
    """
    try:
        print(f"INFO: Extracting text from PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Extract text to TXT file
        txt_path = pdf_converter.pdf_to_text(file_path, output_name=output_name)
        filename = os.path.basename(txt_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error extracting text from PDF: {str(e)}"

# --- Tool: Compress PDF ------------------------------------------------------
@tool
def compress_pdf_file(file_path: str, output_name: str = None, compression_level: str = 'medium', *, config: RunnableConfig) -> str:
    """
    Compress a PDF file by reducing image quality and removing metadata.
    Helps reduce file size for easier sharing and storage.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename (without extension)
        compression_level: 'low', 'medium', or 'high' (default: 'medium')

    Returns:
        Download link for the compressed PDF
    """
    try:
        print(f"INFO: Compressing PDF with {compression_level} compression: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get original file size
        original_size = os.path.getsize(file_path) / 1024  # KB

        # Compress PDF
        compressed_path = pdf_converter.compress_pdf(file_path, output_name=output_name, compression_level=compression_level)
        filename = os.path.basename(compressed_path)

        # Get compressed file size
        compressed_size = os.path.getsize(compressed_path) / 1024  # KB
        reduction = ((original_size - compressed_size) / original_size) * 100

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error compressing PDF: {str(e)}"

# --- Tool: Split PDF ---------------------------------------------------------
@tool
def split_pdf_file(file_path: str, pages: str = 'all', output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Split a PDF into separate files by page ranges or individual pages.
    Useful for extracting specific pages or breaking up large documents.

    Args:
        file_path: Path to the PDF file
        pages: How to split the PDF:
               - 'all': Split every page into separate files (one page per file)
               - '1-3,4-end': Pages 1-3 in one PDF, pages 4-end in another PDF
               - '1-5,6-10': Pages 1-5 in one PDF, pages 6-10 in another PDF
               - '1,3,5': Individual pages in separate files
        output_name: Optional base name for output files (without extension)

    Examples:
        - pages='all' → Creates N separate PDFs (one per page)
        - pages='1-3,4-end' → Creates 2 PDFs (pages 1-3 and pages 4-end)
        - pages='1-2,3-4,5-6' → Creates 3 PDFs with specified ranges

    Returns:
        List of download links for the split PDF files
    """
    try:
        print(f"INFO: Splitting PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Split PDF
        split_paths = pdf_converter.split_pdf(file_path, pages=pages, output_name=output_name)

        # Generate HTML response with download links
        # CRITICAL: Return ONLY raw HTML - no prose text that AI can paraphrase
        html_parts = []

        for i, pdf_path in enumerate(split_paths, 1):
            filename = os.path.basename(pdf_path)
            # Extract page info from filename for better labels
            if 'pages' in filename:
                # Extract page range from filename like "part1_pages1-3.pdf"
                import re
                match = re.search(r'pages(\d+)-(\d+)', filename)
                if match:
                    label = f"📄 Part {i}: Pages {match.group(1)}-{match.group(2)}"
                else:
                    label = f"📄 {filename}"
            elif '_page_' in filename:
                # Single page files like "file_page_1.pdf"
                match = re.search(r'_page_(\d+)', filename)
                if match:
                    label = f"📄 Page {match.group(1)}"
                else:
                    label = f"📄 {filename}"
            else:
                label = f"📄 {filename}"

            html_parts.append(f'<a href="/documents/{filename}" download>{label}</a><br>\n')

        # Return ONLY the HTML - no "Successfully split" text that AI will paraphrase
        return "".join(html_parts)

    except Exception as e:
        return f"❌ Error splitting PDF: {str(e)}"

# --- Tool: Rotate PDF --------------------------------------------------------
@tool
def rotate_pdf_pages(file_path: str, rotation: int = 90, pages: str = 'all', output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Rotate PDF pages by specified degrees (90, 180, 270, or -90).
    Useful for fixing incorrectly oriented pages.

    Args:
        file_path: Path to the PDF file
        rotation: Rotation angle (90, 180, 270, or -90 degrees)
        pages: 'all' to rotate all pages, or specific page numbers
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the rotated PDF
    """
    try:
        print(f"INFO: Rotating PDF by {rotation} degrees: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Rotate PDF
        rotated_path = pdf_converter.rotate_pdf(file_path, rotation=rotation, pages=pages, output_name=output_name)
        filename = os.path.basename(rotated_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error rotating PDF: {str(e)}"

# --- Tool: PDF to CSV --------------------------------------------------------
@tool
def convert_pdf_to_csv(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Extract tables from PDF and convert to CSV format.
    Useful for extracting data tables from PDF reports and documents.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated CSV file
    """
    try:
        print(f"INFO: Converting PDF tables to CSV: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Convert PDF to CSV
        csv_path = pdf_converter.pdf_to_csv(file_path, output_name=output_name)
        filename = os.path.basename(csv_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PDF to CSV: {str(e)}"

# --- Tool: CSV to PDF --------------------------------------------------------
@tool
def convert_csv_to_pdf(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert CSV data to a formatted PDF table.
    Creates a professional-looking PDF from spreadsheet data.

    Args:
        file_path: Path to the CSV file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated PDF
    """
    try:
        print(f"INFO: Converting CSV to PDF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: CSV file not found at {file_path}"

        # Convert CSV to PDF
        pdf_path = pdf_converter.csv_to_pdf(file_path, output_name=output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📊 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting CSV to PDF: {str(e)}"

# --- Tool: HTML to PDF -------------------------------------------------------
@tool
def convert_html_to_pdf(html_input: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert HTML content to PDF format.
    Can accept either an HTML file path or raw HTML string.

    Args:
        html_input: Path to HTML file or raw HTML string
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated PDF
    """
    try:
        print(f"INFO: Converting HTML to PDF")

        # Convert HTML to PDF
        pdf_path = pdf_converter.html_to_pdf(html_input, output_name=output_name)
        filename = os.path.basename(pdf_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting HTML to PDF: {str(e)}"

# --- Tool: PDF to HTML -------------------------------------------------------
@tool
def convert_pdf_to_html(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert PDF document to HTML format.
    Extracts text and tables and generates an HTML page.

    Args:
        file_path: Path to the PDF file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated HTML file
    """
    try:
        print(f"INFO: Converting PDF to HTML: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PDF file not found at {file_path}"

        # Get PDF info
        pdf_info = pdf_converter.get_pdf_info(file_path)
        page_count = pdf_info.get('pages', 0)

        # Convert PDF to HTML
        html_path = pdf_converter.pdf_to_html(file_path, output_name=output_name)
        filename = os.path.basename(html_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

    except Exception as e:
        return f"❌ Error converting PDF to HTML: {str(e)}"

# === IMAGE CONVERSION TOOLS ==================================================

# --- Tool: JPEG to PNG -------------------------------------------------------
@tool
def convert_jpeg_to_png(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert JPEG image to PNG format.
    PNG supports transparency and lossless compression.

    Args:
        file_path: Path to the JPEG file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated PNG image
    """
    try:
        print(f"INFO: Converting JPEG to PNG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: JPEG file not found at {file_path}"

        png_path = image_converter.jpeg_to_png(file_path, output_name=output_name)
        filename = os.path.basename(png_path)

        return f'✅ Successfully converted JPEG to PNG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting JPEG to PNG: {str(e)}"

# --- Tool: PNG to JPEG -------------------------------------------------------
@tool
def convert_png_to_jpeg(file_path: str, output_name: str = None, quality: int = 95, *, config: RunnableConfig) -> str:
    """
    Convert PNG image to JPEG format.
    JPEG has smaller file sizes but doesn't support transparency.

    Args:
        file_path: Path to the PNG file
        output_name: Optional output filename (without extension)
        quality: JPEG quality 1-100 (default 95)

    Returns:
        Download link for the generated JPEG image
    """
    try:
        print(f"INFO: Converting PNG to JPEG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: PNG file not found at {file_path}"

        jpeg_path = image_converter.png_to_jpeg(file_path, output_name=output_name, quality=quality)
        filename = os.path.basename(jpeg_path)

        return f'✅ Successfully converted PNG to JPEG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting PNG to JPEG: {str(e)}"

# --- Tool: WEBP to PNG -------------------------------------------------------
@tool
def convert_webp_to_png(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert WEBP image to PNG format.
    Useful for converting modern web images to widely supported PNG.

    Args:
        file_path: Path to the WEBP file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated PNG image
    """
    try:
        print(f"INFO: Converting WEBP to PNG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: WEBP file not found at {file_path}"

        png_path = image_converter.webp_to_png(file_path, output_name=output_name)
        filename = os.path.basename(png_path)

        return f'✅ Successfully converted WEBP to PNG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting WEBP to PNG: {str(e)}"

# --- Tool: WEBP to JPEG ------------------------------------------------------
@tool
def convert_webp_to_jpeg(file_path: str, output_name: str = None, quality: int = 95, *, config: RunnableConfig) -> str:
    """
    Convert WEBP image to JPEG format.
    Good for compatibility with older systems.

    Args:
        file_path: Path to the WEBP file
        output_name: Optional output filename (without extension)
        quality: JPEG quality 1-100 (default 95)

    Returns:
        Download link for the generated JPEG image
    """
    try:
        print(f"INFO: Converting WEBP to JPEG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: WEBP file not found at {file_path}"

        jpeg_path = image_converter.webp_to_jpeg(file_path, output_name=output_name, quality=quality)
        filename = os.path.basename(jpeg_path)

        return f'✅ Successfully converted WEBP to JPEG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting WEBP to JPEG: {str(e)}"

# --- Tool: HEIC to JPEG ------------------------------------------------------
@tool
def convert_heic_to_jpeg(file_path: str, output_name: str = None, quality: int = 95, *, config: RunnableConfig) -> str:
    """
    Convert HEIC/HEIF image to JPEG format.
    Perfect for converting iPhone photos to universal format.

    Args:
        file_path: Path to the HEIC file
        output_name: Optional output filename (without extension)
        quality: JPEG quality 1-100 (default 95)

    Returns:
        Download link for the generated JPEG image
    """
    try:
        print(f"INFO: Converting HEIC to JPEG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: HEIC file not found at {file_path}"

        jpeg_path = image_converter.heic_to_jpeg(file_path, output_name=output_name, quality=quality)
        filename = os.path.basename(jpeg_path)

        return f'✅ Successfully converted HEIC to JPEG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting HEIC to JPEG: {str(e)}"

# --- Tool: GIF to PNG --------------------------------------------------------
@tool
def convert_gif_to_png(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert GIF to PNG format (extracts first frame).
    Converts animated GIFs to static PNG images.

    Args:
        file_path: Path to the GIF file
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the generated PNG image
    """
    try:
        print(f"INFO: Converting GIF to PNG: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: GIF file not found at {file_path}"

        png_path = image_converter.gif_to_png(file_path, output_name=output_name)
        filename = os.path.basename(png_path)

        return f'✅ Successfully converted GIF to PNG: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting GIF to PNG: {str(e)}"

# --- Tool: Resize Image ------------------------------------------------------
@tool
def resize_uploaded_image(file_path: str, width: int = None, height: int = None,
                         output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Resize image to specified dimensions while maintaining aspect ratio.
    Great for reducing image file sizes or creating thumbnails.

    Args:
        file_path: Path to the image file
        width: Target width in pixels (optional)
        height: Target height in pixels (optional)
        output_name: Optional output filename

    Returns:
        Download link for the resized image
    """
    try:
        print(f"INFO: Resizing image: {file_path} to {width}x{height}")

        if not os.path.exists(file_path):
            return f"❌ Error: Image file not found at {file_path}"

        if not width and not height:
            return "❌ Error: Please specify at least width or height for resizing"

        resized_path = image_converter.resize_image(file_path, width=width, height=height,
                                                   output_name=output_name, maintain_aspect=True)
        filename = os.path.basename(resized_path)

        return f'✅ Successfully resized image to {width or "auto"}x{height or "auto"}: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error resizing image: {str(e)}"

# --- Tool: Compress Image ----------------------------------------------------
@tool
def compress_uploaded_image(file_path: str, output_name: str = None,
                           quality: int = 85, *, config: RunnableConfig) -> str:
    """
    Compress image to reduce file size while maintaining quality.
    Perfect for optimizing images for web or email.

    Args:
        file_path: Path to the image file
        output_name: Optional output filename
        quality: Compression quality 1-100 (default 85)

    Returns:
        Download link for the compressed image with size reduction info
    """
    try:
        print(f"INFO: Compressing image: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Image file not found at {file_path}"

        # Get original file size
        original_size = os.path.getsize(file_path) / 1024  # KB

        compressed_path = image_converter.compress_image(file_path, output_name=output_name,
                                                        quality=quality, optimization='medium')
        filename = os.path.basename(compressed_path)

        # Get compressed file size
        compressed_size = os.path.getsize(compressed_path) / 1024  # KB
        reduction = ((original_size - compressed_size) / original_size) * 100

        return f'✅ Successfully compressed image from {original_size:.1f}KB to {compressed_size:.1f}KB ({reduction:.1f}% reduction): <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error compressing image: {str(e)}"

# --- Tool: Convert to Grayscale ----------------------------------------------
@tool
def convert_image_to_grayscale(file_path: str, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert color image to grayscale (black and white).
    Artistic effect or for reducing file size.

    Args:
        file_path: Path to the image file
        output_name: Optional output filename

    Returns:
        Download link for the grayscale image
    """
    try:
        print(f"INFO: Converting image to grayscale: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Image file not found at {file_path}"

        grayscale_path = image_converter.convert_to_grayscale(file_path, output_name=output_name)
        filename = os.path.basename(grayscale_path)

        return f'✅ Successfully converted image to grayscale: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting to grayscale: {str(e)}"

# --- Tool: Rotate Image ------------------------------------------------------
@tool
def rotate_uploaded_image(file_path: str, angle: int = 90, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Rotate image by specified angle.
    Useful for fixing image orientation.

    Args:
        file_path: Path to the image file
        angle: Rotation angle in degrees (90, 180, 270, etc.)
        output_name: Optional output filename

    Returns:
        Download link for the rotated image
    """
    try:
        print(f"INFO: Rotating image by {angle} degrees: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Image file not found at {file_path}"

        rotated_path = image_converter.rotate_image(file_path, angle=angle, output_name=output_name)
        filename = os.path.basename(rotated_path)

        return f'✅ Successfully rotated image by {angle}°: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error rotating image: {str(e)}"


# =============================================================================
# PHASE 1 & 2 TOOLS (Oct 2025 - 1.65M monthly searches!)
# =============================================================================

# --- TEXT TOOLS (500K monthly searches) -------------------------------------

@tool
def count_words(text: str, *, config: RunnableConfig) -> str:
    """
    Count words, characters, sentences, paragraphs in text.
    Also estimates reading time.

    Args:
        text: The text to analyze

    Returns:
        Statistics about the text formatted as HTML table
    """
    try:
        stats = text_tools.word_counter(text)

        result = f"""✅ Text Statistics:
<div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin: 8px 0;">
<table style="width: 100%; border-collapse: collapse;">
<tr><td style="padding: 4px;"><strong>Words:</strong></td><td>{stats['words']:,}</td></tr>
<tr><td style="padding: 4px;"><strong>Characters (with spaces):</strong></td><td>{stats['characters']:,}</td></tr>
<tr><td style="padding: 4px;"><strong>Characters (no spaces):</strong></td><td>{stats['characters_no_spaces']:,}</td></tr>
<tr><td style="padding: 4px;"><strong>Sentences:</strong></td><td>{stats['sentences']:,}</td></tr>
<tr><td style="padding: 4px;"><strong>Paragraphs:</strong></td><td>{stats['paragraphs']:,}</td></tr>
<tr><td style="padding: 4px;"><strong>Reading Time:</strong></td><td>{stats['reading_time_minutes']} min</td></tr>
</table>
</div>"""
        return result

    except Exception as e:
        return f"❌ Error counting words: {str(e)}"


@tool
def convert_text_case(text: str, case_type: str, *, config: RunnableConfig) -> str:
    """
    Convert text to different cases.

    Args:
        text: The text to convert
        case_type: Type of conversion - 'upper', 'lower', 'title', 'sentence', 'alternating', 'inverse'

    Returns:
        Converted text
    """
    try:
        result = text_tools.case_converter(text, case_type)
        return f"✅ Converted to {case_type} case:\n\n{result}"

    except Exception as e:
        return f"❌ Error converting case: {str(e)}"


@tool
def format_text(text: str, remove_extra_spaces: bool = True, remove_extra_line_breaks: bool = True, trim_lines: bool = True, *, config: RunnableConfig) -> str:
    """
    Clean and format text by removing extra spaces and line breaks.

    Args:
        text: The text to format
        remove_extra_spaces: Remove multiple consecutive spaces
        remove_extra_line_breaks: Remove multiple consecutive line breaks
        trim_lines: Trim whitespace from start/end of each line

    Returns:
        Formatted text
    """
    try:
        result = text_tools.text_formatter(text, remove_extra_spaces, remove_extra_line_breaks, trim_lines)
        return f"✅ Text formatted successfully:\n\n{result}"

    except Exception as e:
        return f"❌ Error formatting text: {str(e)}"


@tool
def generate_lorem_ipsum(count: int = 5, unit: str = 'paragraphs', *, config: RunnableConfig) -> str:
    """
    Generate Lorem Ipsum placeholder text.

    Args:
        count: Number of units to generate
        unit: Type of unit - 'paragraphs', 'sentences', 'words'

    Returns:
        Generated Lorem Ipsum text
    """
    try:
        result = text_tools.lorem_ipsum_generator(count, unit)
        return f"✅ Generated {count} {unit} of Lorem Ipsum:\n\n{result}"

    except Exception as e:
        return f"❌ Error generating Lorem Ipsum: {str(e)}"


@tool
def find_replace_text(text: str, find: str, replace: str, case_sensitive: bool = True, whole_word: bool = False, *, config: RunnableConfig) -> str:
    """
    Find and replace text in bulk.

    Args:
        text: The text to search in
        find: Text to find
        replace: Text to replace with
        case_sensitive: Whether search is case sensitive
        whole_word: Whether to match whole words only

    Returns:
        Modified text with replacement count
    """
    try:
        result, count = text_tools.find_and_replace(text, find, replace, case_sensitive, whole_word)
        return f"✅ Replaced {count} occurrence(s) of '{find}' with '{replace}':\n\n{result}"

    except Exception as e:
        return f"❌ Error finding and replacing: {str(e)}"


@tool
def generate_password(length: int = 16, include_uppercase: bool = True, include_lowercase: bool = True, include_numbers: bool = True, include_symbols: bool = True, *, config: RunnableConfig) -> str:
    """
    Generate a secure random password.

    Args:
        length: Password length (minimum 4)
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_numbers: Include numbers
        include_symbols: Include symbols

    Returns:
        Generated password
    """
    try:
        password = text_tools.password_generator(length, include_uppercase, include_lowercase, include_numbers, include_symbols)
        return f"✅ Generated secure password ({length} characters):\n\n<code style='font-size: 18px; background: #f0f0f0; padding: 8px; border-radius: 4px;'>{password}</code>"

    except Exception as e:
        return f"❌ Error generating password: {str(e)}"


# --- QR CODE & BARCODE TOOLS (400K monthly searches) -------------------------

@tool
def create_qr_code(data: str, size: int = 10, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Generate a QR code for text, URL, or other data.

    Args:
        data: Data to encode (text, URL, etc.)
        size: QR code size (1-40, default 10)
        output_name: Optional output filename

    Returns:
        QR code image with download link
    """
    try:
        print(f"INFO: Generating QR code for: {data[:50]}...")

        qr_path = qr_barcode_tools.generate_qr_code(data, output_path=output_name if output_name else None, size=size)
        filename = os.path.basename(qr_path)

        return f'✅ QR code generated successfully: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error generating QR code: {str(e)}"


@tool
def create_wifi_qr(ssid: str, password: str = None, security: str = 'WPA', *, config: RunnableConfig) -> str:
    """
    Generate a WiFi QR code for easy network connection.

    Args:
        ssid: WiFi network name
        password: WiFi password (optional for open networks)
        security: Security type - 'WPA', 'WEP', or 'nopass'

    Returns:
        WiFi QR code image with download link
    """
    try:
        print(f"INFO: Generating WiFi QR code for network: {ssid}")

        qr_path = qr_barcode_tools.generate_wifi_qr(ssid, password, security)
        filename = os.path.basename(qr_path)

        return f'✅ WiFi QR code generated successfully: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error generating WiFi QR code: {str(e)}"


@tool
def create_barcode(data: str, barcode_type: str = 'code128', output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Generate a barcode image.

    Args:
        data: Data to encode
        barcode_type: Type of barcode - 'code128', 'code39', 'ean13', 'ean8', 'upca', 'isbn13', etc.
        output_name: Optional output filename

    Returns:
        Barcode image with download link
    """
    try:
        print(f"INFO: Generating {barcode_type} barcode for: {data}")

        barcode_path = qr_barcode_tools.generate_barcode(data, barcode_type, output_path=output_name if output_name else None)
        filename = os.path.basename(barcode_path)

        return f'✅ Barcode generated successfully: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error generating barcode: {str(e)}"


# --- AUDIO TOOLS (400K monthly searches) -------------------------------------

@tool
def extract_audio_from_video(file_path: str, bitrate: str = '192k', output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Extract audio from MP4 video and save as MP3.

    Args:
        file_path: Path to the video file
        bitrate: MP3 bitrate - '128k', '192k', '256k', '320k'
        output_name: Optional output filename

    Returns:
        Download link for the extracted MP3 audio
    """
    try:
        print(f"INFO: Extracting audio from video: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Video file not found at {file_path}"

        mp3_path = audio_tools.mp4_to_mp3(file_path, output_name, bitrate)
        filename = os.path.basename(mp3_path)

        return f'✅ Audio extracted successfully: <a href="/assets/{filename}" download class="download-link">Download MP3</a>'

    except Exception as e:
        return f"❌ Error extracting audio: {str(e)}"


@tool
def convert_audio_format(file_path: str, output_format: str, bitrate: str = None, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert audio files between formats.

    Args:
        file_path: Path to the audio file
        output_format: Desired format - 'mp3', 'wav', 'm4a', 'ogg', 'flac'
        bitrate: Audio bitrate (e.g., '128k', '192k', '256k')
        output_name: Optional output filename

    Returns:
        Download link for the converted audio
    """
    try:
        print(f"INFO: Converting audio to {output_format}: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Audio file not found at {file_path}"

        converted_path = audio_tools.audio_converter(file_path, output_format, output_name, bitrate)
        filename = os.path.basename(converted_path)

        return f'✅ Audio converted to {output_format.upper()}: <a href="/assets/{filename}" download class="download-link">Download {output_format.upper()}</a>'

    except Exception as e:
        return f"❌ Error converting audio: {str(e)}"


@tool
def compress_audio_file(file_path: str, compression_level: str = 'medium', output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Compress audio file to reduce file size.

    Args:
        file_path: Path to the audio file
        compression_level: Compression level - 'low', 'medium', 'high'
        output_name: Optional output filename

    Returns:
        Download link for the compressed audio
    """
    try:
        print(f"INFO: Compressing audio file: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Audio file not found at {file_path}"

        compressed_path = audio_tools.compress_audio(file_path, output_name, compression_level)
        filename = os.path.basename(compressed_path)

        return f'✅ Audio compressed successfully: <a href="/assets/{filename}" download class="download-link">Download Compressed Audio</a>'

    except Exception as e:
        return f"❌ Error compressing audio: {str(e)}"


@tool
def trim_audio_file(file_path: str, start_time: float, end_time: float = None, duration: float = None, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Trim/cut audio file by time range.

    Args:
        file_path: Path to the audio file
        start_time: Start time in seconds
        end_time: End time in seconds (optional if duration specified)
        duration: Duration in seconds from start (optional if end_time specified)
        output_name: Optional output filename

    Returns:
        Download link for the trimmed audio
    """
    try:
        print(f"INFO: Trimming audio file: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Audio file not found at {file_path}"

        trimmed_path = audio_tools.trim_audio(file_path, start_time, end_time, duration, output_name)
        filename = os.path.basename(trimmed_path)

        return f'✅ Audio trimmed successfully: <a href="/assets/{filename}" download class="download-link">Download Trimmed Audio</a>'

    except Exception as e:
        return f"❌ Error trimming audio: {str(e)}"


@tool
def merge_audio_files(file_paths: List[str], crossfade_duration: float = 0, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Merge/combine multiple audio files into one.

    Args:
        file_paths: List of audio file paths to merge (in order)
        crossfade_duration: Crossfade duration in seconds between tracks (default 0)
        output_name: Optional output filename

    Returns:
        Download link for the merged audio
    """
    try:
        print(f"INFO: Merging {len(file_paths)} audio files")

        # Validate all files exist
        for path in file_paths:
            if not os.path.exists(path):
                return f"❌ Error: Audio file not found at {path}"

        merged_path = audio_tools.merge_audio(file_paths, output_name, crossfade_duration)
        filename = os.path.basename(merged_path)

        return f'✅ {len(file_paths)} audio files merged successfully: <a href="/assets/{filename}" download class="download-link">Download Merged Audio</a>'

    except Exception as e:
        return f"❌ Error merging audio: {str(e)}"


# --- VIDEO TOOLS (350K monthly searches) -------------------------------------

@tool
def convert_video_to_gif(file_path: str, start_time: float = 0, duration: float = None, fps: int = 10, width: int = None, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Convert video to animated GIF.

    Args:
        file_path: Path to the video file
        start_time: Start time in seconds (default 0)
        duration: Duration in seconds from start (None = full video)
        fps: Frames per second for GIF (default 10)
        width: Output width in pixels (maintains aspect ratio)
        output_name: Optional output filename

    Returns:
        GIF image with preview
    """
    try:
        print(f"INFO: Converting video to GIF: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Video file not found at {file_path}"

        gif_path = video_tools.video_to_gif(file_path, output_name, start_time, duration, fps, width)
        filename = os.path.basename(gif_path)

        return f'✅ Video converted to GIF: <img src="/assets/{filename}" class="message-image" onclick="openImageModal(\'/assets/{filename}\')">'

    except Exception as e:
        return f"❌ Error converting video to GIF: {str(e)}"


@tool
def compress_video_file(file_path: str, quality: str = 'medium', target_resolution: str = None, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Compress video to reduce file size.

    Args:
        file_path: Path to the video file
        quality: Compression quality - 'low', 'medium', 'high'
        target_resolution: Target resolution - '1080p', '720p', '480p', '360p'
        output_name: Optional output filename

    Returns:
        Download link for the compressed video
    """
    try:
        print(f"INFO: Compressing video: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Video file not found at {file_path}"

        compressed_path = video_tools.compress_video(file_path, output_name, quality, target_resolution)
        filename = os.path.basename(compressed_path)

        return f'✅ Video compressed successfully: <video src="/videos/{filename}" controls style="max-width: 100%; border-radius: 8px; margin: 8px 0;"></video>'

    except Exception as e:
        return f"❌ Error compressing video: {str(e)}"


@tool
def trim_video_file(file_path: str, start_time: float, end_time: float = None, duration: float = None, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Trim/cut video by time range.

    Args:
        file_path: Path to the video file
        start_time: Start time in seconds
        end_time: End time in seconds (optional if duration specified)
        duration: Duration in seconds from start (optional if end_time specified)
        output_name: Optional output filename

    Returns:
        Trimmed video with player
    """
    try:
        print(f"INFO: Trimming video: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Video file not found at {file_path}"

        trimmed_path = video_tools.trim_video(file_path, start_time, end_time, duration, output_name)
        filename = os.path.basename(trimmed_path)

        return f'✅ Video trimmed successfully: <video src="/videos/{filename}" controls style="max-width: 100%; border-radius: 8px; margin: 8px 0;"></video>'

    except Exception as e:
        return f"❌ Error trimming video: {str(e)}"


@tool
def change_video_speed(file_path: str, speed_factor: float, output_name: str = None, *, config: RunnableConfig) -> str:
    """
    Change video playback speed (speed up or slow down).

    Args:
        file_path: Path to the video file
        speed_factor: Speed multiplier (0.5=half speed, 2.0=double speed, etc.)
        output_name: Optional output filename

    Returns:
        Speed-adjusted video with player
    """
    try:
        print(f"INFO: Changing video speed to {speed_factor}x: {file_path}")

        if not os.path.exists(file_path):
            return f"❌ Error: Video file not found at {file_path}"

        adjusted_path = video_tools.change_video_speed(file_path, speed_factor, output_name)
        filename = os.path.basename(adjusted_path)

        return f'✅ Video speed changed to {speed_factor}x: <video src="/videos/{filename}" controls style="max-width: 100%; border-radius: 8px; margin: 8px 0;"></video>'

    except Exception as e:
        return f"❌ Error changing video speed: {str(e)}"


# --- Tool: Convert All Documents to PDF and Merge ---------------------------
@tool
def convert_and_merge_documents(file_paths: List[str], output_name: str = "combined_document", *, config: RunnableConfig) -> str:
    """
    Convert all uploaded documents (Word, Excel, PowerPoint, Images) to PDF format and merge them into a single PDF.
    This is a one-stop tool for combining mixed document types.

    Args:
        file_paths: List of document file paths (can be mix of PDF, DOCX, XLSX, PPTX, images, etc.)
        output_name: Optional output filename (without extension)

    Returns:
        Download link for the merged PDF containing all documents
    """
    try:
        if not file_paths or len(file_paths) == 0:
            return "❌ Error: No files provided for conversion and merging."

        print(f"INFO: Converting and merging {len(file_paths)} files")

        converted_pdfs = []
        conversion_details = []

        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"WARNING: File not found: {file_path}")
                conversion_details.append(f"❌ Skipped (not found): {os.path.basename(file_path)}")
                continue

            filename = os.path.basename(file_path)
            ext = file_path.lower().split('.')[-1]

            try:
                if ext == 'pdf':
                    # Already PDF, just add to list
                    converted_pdfs.append(file_path)
                    conversion_details.append(f"✅ {filename} (already PDF)")

                elif ext in ['doc', 'docx']:
                    # Convert Word to PDF
                    pdf_path = pdf_converter.word_to_pdf(file_path)
                    converted_pdfs.append(pdf_path)
                    conversion_details.append(f"✅ {filename} → PDF")

                elif ext in ['xls', 'xlsx']:
                    # Convert Excel to PDF
                    pdf_path = pdf_converter.excel_to_pdf(file_path)
                    converted_pdfs.append(pdf_path)
                    conversion_details.append(f"✅ {filename} → PDF")

                elif ext in ['ppt', 'pptx']:
                    # Convert PowerPoint to PDF
                    pdf_path = pdf_converter.powerpoint_to_pdf(file_path)
                    converted_pdfs.append(pdf_path)
                    conversion_details.append(f"✅ {filename} → PDF")

                elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                    # Convert image to PDF
                    pdf_path = pdf_converter.images_to_pdf([file_path])
                    converted_pdfs.append(pdf_path)
                    conversion_details.append(f"✅ {filename} → PDF")

                else:
                    conversion_details.append(f"⚠️ Skipped (unsupported format): {filename}")

            except Exception as e:
                print(f"ERROR: Failed to convert {filename}: {e}")
                conversion_details.append(f"❌ Failed: {filename} - {str(e)}")

        if len(converted_pdfs) == 0:
            return "❌ Error: No files could be converted to PDF. Please check the file formats."

        if len(converted_pdfs) == 1:
            # Only one file, return it directly
            filename = os.path.basename(converted_pdfs[0])
            # Return ONLY raw HTML - no prose text that AI can paraphrase
            return f'<a href="/documents/{filename}" download>📄 {filename}</a>'

        # Merge all PDFs
        merged_path = pdf_converter.merge_pdfs(converted_pdfs, output_name)
        merged_filename = os.path.basename(merged_path)

        # Return ONLY raw HTML - no prose text that AI can paraphrase
        return f'<a href="/documents/{merged_filename}" download>📄 {merged_filename}</a>'

    except Exception as e:
        return f"❌ Error converting and merging documents: {str(e)}"

# =============================================================================

@tool
def analyze_user_intent(user_request: str) -> str:
    """
    Analyze what the user is asking for and determine the best approach.
    Use this first to understand complex requests.
    """
    request_lower = user_request.lower()
    
    # Identify task components
    needs_search = any(word in request_lower for word in ['news', 'latest', 'current', 'today', 'recent', 'indore'])
    needs_image_gen = any(word in request_lower for word in ['create', 'generate', 'make', 'draw', 'design', 'image'])
    needs_image_edit = any(word in request_lower for word in ['edit', 'modify', 'change', 'add to', 'update'])
    needs_writing = any(word in request_lower for word in ['post', 'write', 'compose', 'linkedin', 'social'])
    
    # Count total tasks
    task_count = sum([needs_search, needs_image_gen, needs_image_edit, needs_writing])
    
    if task_count > 1:
        return f"I understand you want me to handle multiple tasks: {user_request}. I'll start with the first step now."
    else:
        return f"I'll help you with: {user_request}"

# --- Master coordinator agent ----------------------------------------------
def build_coordinator():
    # Using OpenAI GPT-4o for superior reasoning and multi-step planning
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Give the coordinator access to ALL tools for sequential execution
    tools = [
        search_web,
        generate_image,
        edit_image,
        generate_video_from_text,
        generate_video_from_image,
        generate_image_from_multiple,
        analyze_user_intent,
        evaluate_result_quality,
        check_image_context,
        # PDF Conversion tools - FROM PDF
        convert_pdf_to_images,
        convert_pdf_to_word,
        convert_pdf_to_excel,
        convert_pdf_to_powerpoint,
        # Office Conversion tools - TO PDF
        convert_word_to_pdf,
        convert_excel_to_pdf,
        convert_powerpoint_to_pdf,
        convert_image_file_to_pdf,
        convert_images_to_pdf,
        # Extended Format Conversions
        convert_excel_to_csv,
        convert_csv_to_excel,
        convert_word_to_txt,
        convert_excel_to_txt,
        convert_word_to_html,
        convert_excel_to_html,
        convert_powerpoint_to_html,
        # PDF Utilities
        merge_pdfs,
        convert_and_merge_documents,
        # New PDF Features (Oct 2025)
        extract_text_from_pdf,
        compress_pdf_file,
        split_pdf_file,
        rotate_pdf_pages,
        convert_pdf_to_csv,
        convert_csv_to_pdf,
        convert_html_to_pdf,
        convert_pdf_to_html,
        # Image Format Conversions (Oct 2025)
        convert_jpeg_to_png,
        convert_png_to_jpeg,
        convert_webp_to_png,
        convert_webp_to_jpeg,
        convert_heic_to_jpeg,
        convert_gif_to_png,
        # Image Manipulation Tools
        resize_uploaded_image,
        compress_uploaded_image,
        convert_image_to_grayscale,
        rotate_uploaded_image,
        # Phase 1 & 2 Tools (Oct 2025 - 1.65M monthly searches!)
        # Text Tools (500K searches)
        count_words,
        convert_text_case,
        format_text,
        generate_lorem_ipsum,
        find_replace_text,
        generate_password,
        # QR Codes & Barcodes (400K searches)
        create_qr_code,
        create_wifi_qr,
        create_barcode
        # TEMPORARILY DISABLED - Audio/Video tools causing deployment issues
        # # Audio Tools (400K searches)
        # extract_audio_from_video,
        # convert_audio_format,
        # compress_audio_file,
        # trim_audio_file,
        # merge_audio_files,
        # # Video Tools (350K searches)
        # convert_video_to_gif,
        # compress_video_file,
        # trim_video_file,
        # change_video_speed
    ]
    
    prompt = (
        "You are an intelligent AI coordinator powered by GPT-4o. You excel at understanding user intent and executing complex multi-step tasks.\n\n"
        "CRITICAL STOP CONDITIONS:\n"
        "1. NEVER call the same tool with IDENTICAL parameters - vary descriptions/prompts for multiple calls\n"
        "2. STOP after successfully completing the user's request\n"
        "3. If a tool fails, provide helpful error message and STOP - DO NOT RETRY\n"
        "4. Maximum 10 tool calls per response (to allow bulk operations like '5 different styles')\n"
        "5. For bulk image operations (e.g. '5 different styles'), you CAN call edit_image or generate_image multiple times with DIFFERENT prompts\n"
        "6. NEVER call generate_image_from_multiple more than ONCE per response\n"
        "7. If a tool fails, do NOT retry with same parameters - explain the issue\n"
        "8. NEVER call check_image_context and then edit_image in the same response\n\n"
        "CRITICAL: When you receive a message with image content AND animation/video keywords, immediately use generate_video_from_image tool.\n\n"
        "CORE BEHAVIOR:\n"
        "1. Analyze user requests to understand all required steps\n"
        "2. When user uploads image(s), they are IMMEDIATELY available for operations\n"
        "3. ONLY use check_image_context if you're unsure about image availability\n"
        "4. For multi-step requests, execute ALL steps in sequence within your response\n"
        "5. Use tools in logical order and show results after each step\n\n"
        "AVAILABLE TOOLS:\n"
        "- analyze_user_intent: Understand complex requests\n"
        "- check_image_context: Check what images are available for operations\n"
        "- search_web: Get current news and information\n"
        "- generate_image: Create images from descriptions using nano-banana\n"
        "- edit_image: Modify uploaded images using nano-banana/edit\n"
        "- generate_video_from_text: Create videos from text prompts using LTX-Video-13B\n"
        "- generate_video_from_image: Animate existing images into videos using LTX-Video-13B\n"
        "- generate_image_from_multiple: Combine multiple uploaded images using nano-banana/edit\n"
        "- convert_pdf_to_images: Convert PDF pages to PNG or JPG images (specify output_format='png' or output_format='jpg')\n"
        "- convert_pdf_to_word: Convert PDF to Word (DOCX) format\n"
        "- convert_pdf_to_excel: Convert PDF to Excel (XLSX) format\n"
        "- convert_pdf_to_powerpoint: Convert PDF to PowerPoint (PPTX) format\n"
        "- convert_word/excel/powerpoint_to_pdf: Convert Office documents to PDF\n"
        "- convert_excel_to_csv: Convert Excel spreadsheets to CSV format\n"
        "- convert_csv_to_excel: Convert CSV files to Excel spreadsheets\n"
        "- convert_word/excel_to_txt: Convert Word or Excel to plain text\n"
        "- convert_word/excel/powerpoint_to_html: Convert Office documents to HTML web format\n"
        "- convert_and_merge_documents: CRITICAL - Use this for combining/merging multiple documents into single PDF\n"
        "- merge_pdfs: Merge multiple PDF files only (use convert_and_merge_documents for mixed types)\n"
        "- extract_text_from_pdf: Extract all text from PDF to plain text file\n"
        "- compress_pdf_file: Reduce PDF file size by compressing images and removing metadata\n"
        "- split_pdf_file: Split PDF by page ranges - pages='all' for one-per-page, pages='1-3,4-end' for custom ranges\n"
        "- rotate_pdf_pages: Rotate PDF pages by 90/180/270 degrees\n"
        "- convert_pdf_to_csv: Extract tables from PDF to CSV format\n"
        "- convert_csv_to_pdf: Convert CSV data to formatted PDF table\n"
        "- convert_html_to_pdf: Convert HTML content or file to PDF\n"
        "- convert_pdf_to_html: Convert PDF to HTML web page\n"
        "- convert_jpeg_to_png: Convert JPEG images to PNG format\n"
        "- convert_png_to_jpeg: Convert PNG images to JPEG format\n"
        "- convert_webp_to_png: Convert WEBP images to PNG format\n"
        "- convert_webp_to_jpeg: Convert WEBP images to JPEG format\n"
        "- convert_heic_to_jpeg: Convert HEIC/HEIF (iPhone photos) to JPEG\n"
        "- convert_gif_to_png: Convert GIF animations to PNG (first frame)\n"
        "- resize_uploaded_image: Resize images to specified dimensions\n"
        "- compress_uploaded_image: Reduce image file size while maintaining quality\n"
        "- convert_image_to_grayscale: Convert color images to black and white\n"
        "- rotate_uploaded_image: Rotate images by specified angle\n"
        "- count_words: Count words, characters, sentences, paragraphs, and estimate reading time\n"
        "- convert_text_case: Convert text to upper/lower/title/sentence/alternating/inverse case\n"
        "- format_text: Clean and format text by removing extra spaces and line breaks\n"
        "- generate_lorem_ipsum: Generate Lorem Ipsum placeholder text\n"
        "- find_replace_text: Find and replace text in bulk with options\n"
        "- generate_password: Generate secure random passwords with custom settings\n"
        "- create_qr_code: Generate QR codes for text, URLs, or other data\n"
        "- create_wifi_qr: Generate WiFi QR codes for easy network connection\n"
        "- create_barcode: Generate barcodes (EAN, UPC, Code128, etc.)\n"
        # TEMPORARILY DISABLED - Audio/Video tools
        # "- extract_audio_from_video: Extract audio from MP4 video and save as MP3\n"
        # "- convert_audio_format: Convert audio between MP3/WAV/M4A/OGG/FLAC formats\n"
        # "- compress_audio_file: Compress audio to reduce file size\n"
        # "- trim_audio_file: Trim/cut audio files by time range\n"
        # "- merge_audio_files: Merge/combine multiple audio files into one\n"
        # "- convert_video_to_gif: Convert video clips to animated GIF\n"
        # "- compress_video_file: Compress video to reduce file size\n"
        # "- trim_video_file: Trim/cut video by time range\n"
        # "- change_video_speed: Speed up or slow down video playback\n"
        "- evaluate_result_quality: Check if results match user expectations\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 CRITICAL SYSTEM REQUIREMENT - HTML PRESERVATION PROTOCOL 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "YOU ARE IN RAW HTML PASSTHROUGH MODE FOR TOOL OUTPUTS.\n\n"

        "TECHNICAL CONSTRAINT: The frontend is a web application that ONLY renders raw HTML.\n"
        "Markdown syntax will display as broken text. This is a SYSTEM LIMITATION, not a preference.\n\n"

        "🔴 MANDATORY RULE - ZERO TOLERANCE 🔴\n"
        "When a tool returns output containing ANY of these characters: < > href src\n"
        "→ You MUST enter VERBATIM COPY MODE\n"
        "→ Do NOT engage your markdown formatting instinct\n"
        "→ Do NOT summarize, paraphrase, or beautify\n"
        "→ Copy the tool's response BYTE-FOR-BYTE including ALL tags, attributes, and whitespace\n\n"

        "WHY THIS MATTERS:\n"
        "❌ Your output: '📄 Part 1: Pages 1-3[]()' → User sees broken plain text (SYSTEM FAILURE)\n"
        "✅ Tool output: '<a href=\"/documents/file.pdf\" download>📄 Part 1</a>' → User gets working download link\n\n"

        "🎯 CORRECT BEHAVIOR - FOLLOW THIS PATTERN:\n"
        "Step 1: Tool returns → '<a href=\"/documents/Rent_agreement_part1_pages1-3.pdf\" download>📄 Part 1: Pages 1-3</a><br>'\n"
        "Step 2: You detect → Contains '<a href' → ENTER VERBATIM MODE\n"
        "Step 3: You output → '<a href=\"/documents/Rent_agreement_part1_pages1-3.pdf\" download>📄 Part 1: Pages 1-3</a><br>' (EXACT COPY)\n"
        "Step 4: Frontend → Renders clickable download link ✅\n\n"

        "❌ BROKEN BEHAVIOR - NEVER DO THIS:\n"
        "Step 1: Tool returns → '<a href=\"/documents/file.pdf\">📄 test.pdf</a>'\n"
        "Step 2: You think → 'I should make this prettier with markdown'\n"
        "Step 3: You output → '- 📄 test.pdf' or '[test.pdf]()' or 'Here is the file: test.pdf'\n"
        "Step 4: Frontend → Shows plain text, link broken, USER CANNOT DOWNLOAD ❌\n\n"

        "🔒 FORBIDDEN TRANSFORMATIONS - THESE BREAK THE SYSTEM:\n"
        "❌ '<a href=\"/documents/file.pdf\">text</a>' → '[text]()' (markdown link with empty URL)\n"
        "❌ '<a href=\"/documents/file.pdf\">text</a>' → '- text' (bullet list removes link)\n"
        "❌ '<a href=\"/documents/file.pdf\">text</a>' → 'text' (plain text removes link)\n"
        "❌ '<img src=\"/assets/img.png\">' → '![image]()' (markdown image breaks)\n"
        "❌ Adding ANY text before/after the HTML that wasn't in the tool output\n"
        "❌ Removing <br> tags, download attributes, class names, or onclick handlers\n"
        "❌ Converting multiple links to a numbered/bulleted list\n\n"

        "✅ REQUIRED BEHAVIOR - VERBATIM PASSTHROUGH:\n"
        "✅ IF tool output starts with '<' → Copy from first '<' to last '>' including everything between\n"
        "✅ IF tool output contains '<a href' → Output EXACTLY as tool returned it, character-by-character\n"
        "✅ IF tool output contains '<img src' → Output EXACTLY as tool returned it, no markdown conversion\n"
        "✅ IF tool output contains multiple '<a>' tags → Output ALL of them exactly, preserving <br> tags\n"
        "✅ Treat HTML like code in a code block - you wouldn't reformat user's code, don't reformat HTML\n\n"

        "📋 REAL EXAMPLES FROM PRODUCTION:\n\n"

        "Example 1 - Split PDF (Multiple Files):\n"
        "Tool returns: '<a href=\"/documents/Rent_agreement_part1_pages1-3.pdf\" download>📄 Part 1: Pages 1-3</a><br>\\n<a href=\"/documents/Rent_agreement_part2_pages4-6.pdf\" download>📄 Part 2: Pages 4-6</a><br>\\n'\n"
        "✅ CORRECT: '<a href=\"/documents/Rent_agreement_part1_pages1-3.pdf\" download>📄 Part 1: Pages 1-3</a><br>\\n<a href=\"/documents/Rent_agreement_part2_pages4-6.pdf\" download>📄 Part 2: Pages 4-6</a><br>\\n'\n"
        "❌ WRONG: 'Here are the two files:\\n- 📄 Part 1: Pages 1-3\\n- 📄 Part 2: Pages 4-6'\n"
        "❌ WRONG: '📄 Part 1: Pages 1-3[]()\\n📄 Part 2: Pages 4-6[]()'\n\n"

        "Example 2 - Single File Conversion:\n"
        "Tool returns: '<a href=\"/documents/converted_report.docx\" download>📄 converted_report.docx</a>'\n"
        "✅ CORRECT: '<a href=\"/documents/converted_report.docx\" download>📄 converted_report.docx</a>'\n"
        "❌ WRONG: 'Successfully converted! Download: [converted_report.docx]()'\n"
        "❌ WRONG: '📄 converted_report.docx'\n\n"

        "Example 3 - Multiple Images:\n"
        "Tool returns: '<img src=\"/assets/page1.png\" class=\"message-image\" onclick=\"openImageModal(\\'/assets/page1.png\\')\" style=\"max-width: 150px; margin: 5px;\"><img src=\"/assets/page2.png\" class=\"message-image\" onclick=\"openImageModal(\\'/assets/page2.png\\')\" style=\"max-width: 150px; margin: 5px;\">'\n"
        "✅ CORRECT: (copy the EXACT string above with ALL attributes)\n"
        "❌ WRONG: '![Page 1]()\\n![Page 2]()'\n\n"

        "🧠 MENTAL MODEL:\n"
        "Think of yourself as a PROXY SERVER, not a content formatter.\n"
        "When tool output contains HTML:\n"
        "- You are a DUMB PIPE that passes data unchanged\n"
        "- You are NOT a markdown prettifier\n"
        "- You are NOT adding user-friendly descriptions\n"
        "- Your job is MECHANICAL COPYING, not creative writing\n\n"

        "SELF-CHECK BEFORE RESPONDING:\n"
        "1. Does the tool output contain '<a href' or '<img src'? → YES/NO\n"
        "2. If YES → Did I copy it EXACTLY with zero changes? → YES/NO\n"
        "3. If NO to #2 → STOP, re-read this protocol, and output the EXACT HTML\n\n"

        "⚠️ CONSEQUENCE OF VIOLATION:\n"
        "Converting HTML to markdown/plain text breaks the entire application.\n"
        "Users will be unable to download their files.\n"
        "This is a CRITICAL BUG that breaks core functionality.\n"
        "There are ZERO valid reasons to modify HTML tool output.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "MULTI-STEP EXECUTION PATTERN:\n"
        "For complex requests like 'Get news, create video, write post':\n"
        "1. Use analyze_user_intent to acknowledge the full request\n"
        "2. Use search_web to get current information\n"
        "3. Use generate_video_from_text or generate_image based on request\n"
        "4. Write content incorporating all results\n"
        "5. Present everything in a well-organized response\n\n"
        "SMART IMAGE HANDLING:\n"
        "- When the message contains image content blocks, the user has uploaded an image\n"
        "- If message has image + video/animate keywords: use generate_video_from_image directly\n"
        "- If message has image + edit/modify keywords: use edit_image directly\n"
        "- If message contains '[Multi-image request with X uploaded images]': use generate_image_from_multiple directly\n"
        "- If message has multiple images: use generate_image_from_multiple\n"
        "- If message has single image + analysis: analyze the uploaded image directly\n"
        "- If no images uploaded but image requested: use generate_image\n"
        "- Only use check_image_context when you need to verify what's available\n"
        "- IMPORTANT: When generating multiple images then creating a video, the video tool will automatically select the matching image based on your prompt\n\n"
        "SMART DOCUMENT HANDLING:\n"
        "- When user uploads documents and asks to 'combine', 'merge', or 'combine into PDF': use convert_and_merge_documents tool\n"
        "- The convert_and_merge_documents tool handles ALL document types: PDF, Word, Excel, PowerPoint, and images\n"
        "- NEVER make up download links - ALWAYS call the actual tool and use its returned link\n"
        "- Document paths are provided in the message as: 'Uploaded X documents: [filepath1, filepath2, ...]'\n"
        "- Pass the file paths directly to convert_and_merge_documents tool\n\n"
        "FORMAT CONVERSION DECISION LOGIC:\n"
        "- 'convert to csv' or 'export to csv' + Excel file -> Use convert_excel_to_csv\n"
        "- 'convert to excel' or 'make it xlsx' + CSV file -> Use convert_csv_to_excel\n"
        "- 'convert to text' or 'export to txt' + Word/Excel -> Use convert_word_to_txt or convert_excel_to_txt\n"
        "- 'convert to html' or 'make it web page' + Office docs -> Use convert_word/excel/powerpoint_to_html\n"
        "- 'extract text' from Word -> Use convert_word_to_txt\n"
        "- 'raw data' from Excel -> Use convert_excel_to_csv or convert_excel_to_txt\n"
        "- User uploads document and requests specific format -> Use appropriate conversion tool\n"
        "- ALWAYS use the correct source-to-target conversion tool based on uploaded file type and requested output\n\n"
        "DECISION LOGIC:\n"
        "- 'news', 'latest', 'current' -> Use search_web\n"
        "- 'create image', 'generate image' + NO uploads -> Use generate_image\n"
        "- Message contains '[Multi-image request with' -> IMMEDIATELY use generate_image_from_multiple\n"
        "- CURRENT multi-image upload (2-5) -> Use generate_image_from_multiple\n"
        "- 'combine', 'merge' + check_image_context shows 2+ images -> Use generate_image_from_multiple\n"
        "- 'create 2 images' -> Use generate_image twice with different prompts\n"
        "- 'create 5 different styles' or similar BULK requests -> Call edit_image or generate_image 5 times with VARIED prompts\n"
        "- 'create video', 'generate video' + NO images -> Use generate_video_from_text\n"
        "- 'make video of [subject]' -> FIRST use check_image_context, THEN use generate_video_from_image if images available\n"
        "- 'video' or 'animate' request -> ALWAYS check_image_context first to see what's available\n"
        "- Single image uploaded + 'video', 'animate' -> Use generate_video_from_image (NOT generate_image)\n"
        "- Single image uploaded + 'edit', 'modify' -> Use edit_image (NOT generate_image)\n"
        "- Single image uploaded + ANY request (including 'create', 'make', 'wearing') -> Use edit_image to modify the uploaded image\n"
        "- Single image uploaded + 'create X different styles/versions' -> Call edit_image X times with HIGHLY VARIED and DETAILED style prompts\n"
        "  * For style variations: Include specific details like lighting, clothing, background, mood, era, color palette\n"
        "  * Example: Instead of just 'casual style', use 'casual street style with denim jacket, urban graffiti background, golden hour lighting'\n"
        "  * Make each style DRAMATICALLY different to ensure visual diversity\n"
        "- CRITICAL: If user uploads an image, NEVER use generate_image - always use edit_image or generate_video_from_image\n\n"
        "IMAGE CONTEXT HANDLING:\n"
        "- When message contains image content blocks: proceed with the operation immediately\n"
        "- NEVER repeatedly call check_image_context\n"
        "- If user uploads an image in current request, it's available for immediate use\n"
        "- CRITICAL: For single image operations (video, edit), NEVER use generate_image_from_multiple\n"
        "- ONLY use generate_image_from_multiple when user EXPLICITLY uploads multiple images in CURRENT request\n\n"
        "CRITICAL IMAGE OPERATION RULES:\n"
        "1. When message contains image content blocks: user uploaded image, proceed immediately\n"
        "2. Image + 'video'/'animate': use generate_video_from_image (no context check needed)\n"
        "3. Image + 'edit'/'modify': use edit_image (no context check needed)\n"
        "4. Image + ANY other request (create, make, wearing, etc.): use edit_image to modify uploaded image\n"
        "5. NEVER use generate_image when user has uploaded an image - always edit the uploaded image\n"
        "6. NEVER ask for uploads when image content blocks are present\n"
        "7. NEVER use check_image_context when image content blocks are in the message\n"
        "8. STOP after successful completion - do NOT call additional tools\n\n"
        "RESPONSE ACCURACY:\n"
        "- ALWAYS describe exactly what you just did in your own words\n"
        "- NEVER reuse previous responses or descriptions\n"
        "- For image editing: State the specific change you made (e.g., 'I changed the hair to pink' not generic 'I edited the image')\n"
        "- Include timestamps or unique identifiers to ensure response freshness\n"
        "- After each tool use, verify the result matches your current request\n\n"
        "HTML FORMATTING RULES:\n"
        "- ALWAYS preserve ALL HTML tags exactly as returned by tools (img, a, etc.)\n"
        "- When tools return <img src=\\\"/assets/filename\\\" ...> tags, include them EXACTLY in your response\n"
        "- When tools return <a href=\\\"/documents/file\\\" ...> tags, include them EXACTLY in your response\n"
        "- Do NOT convert HTML to markdown - the web interface needs raw HTML\n"
        "- Do NOT add extra text around HTML - include it directly from tool response\n"
        "- Copy the complete HTML from tool results into your response verbatim\n\n"
        "QUALITY CONTROL:\n"
        "- After image editing operations, use evaluate_result_quality to verify the result matches the user's request\n"
        "- If evaluation returns 'INVALID' or 'RETRY', attempt the operation again with improved parameters\n"
        "- Always include the actual edit description in your response (what you changed)\n"
        "- Be specific about what modifications were made to the image\n\n"
        "MULTI-STEP WORKFLOW EXAMPLES:\n"
        "- User: 'create 2 images of man and woman, then combine them' -> 1) generate_image (man), 2) generate_image (woman), 3) check_image_context, 4) generate_image_from_multiple\n"
        "- User: 'combine the images' (after generating multiple) -> 1) check_image_context, 2) generate_image_from_multiple if 2+ images available\n"
        "- User: 'create 3 images: cat, dog, cow' THEN 'make video of dog' -> 1) check_image_context (will show labeled images), 2) generate_video_from_image (will auto-select dog)\n\n"
        "CRITICAL: Execute ALL required steps in sequence. Don't stop after just one tool.\n"
        "Show your work and provide rich, complete responses with accurate descriptions."
    )
    return create_react_agent(model=model, tools=tools, prompt=prompt, name="coordinator")




# --- Unified multi-agent graph ---------------------------------------------
def build_app():
    builder = StateGraph(MessagesState)
    coordinator = build_coordinator()

    # Wrapper node to ensure config is properly passed through
    def coordinator_node(state: dict, *, config: RunnableConfig):
        """Wrapper to ensure RunnableConfig propagates to the coordinator agent"""
        print(f"INFO: coordinator_node invoked with thread_id = {config.get('configurable', {}).get('thread_id', 'MISSING')}")
        # Pass config explicitly to ensure tools receive it
        return coordinator.invoke(state, config=config)

    builder.add_node("coordinator", coordinator_node)
    builder.add_edge(START, "coordinator")
    
    # DISABLED persistence to prevent image bleeding between conversations
    # checkpointer = InMemorySaver()
    
    # Build the app with enhanced configuration
    app = builder.compile()
    
    # Set recursion limit through config instead
    return app

# Add function to completely reset context for testing
def reset_all_context():
    """Reset all global context - for testing purposes"""
    global _thread_image_context, _active_requests, _current_thread_id, _multi_image_active, _global_edit_lock, _thread_recent_edits, _langgraph_execution_tools
    _thread_image_context.clear()
    _active_requests.clear()
    _global_edit_lock.clear()
    _thread_recent_edits.clear()
    _langgraph_execution_tools.clear()
    _current_thread_id = "default"
    _multi_image_active = False

def set_current_thread_id(thread_id):
    """Set the current thread ID for tools to use"""
    global _current_thread_id
    _current_thread_id = thread_id

# Function to clear cached responses for a thread
def clear_thread_cache(thread_id: str):
    """Clear cached responses for a specific thread to prevent response reuse"""
    try:
        global app
        # This will force fresh responses by using a new thread ID variant
        return f"{thread_id}_fresh_{int(time.time())}"
    except:
        return thread_id

app = build_app()

# --- Example runner ---------------------------------------------------------
def encode_image_to_content_block(path: str, mime="image/jpeg"):
    with open(path, "rb") as image_file:
        data = base64.b64encode(image_file.read()).decode("utf-8")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime};base64,{data}"
        }
    }

if __name__ == "__main__":
    # Test the new coordinator system
    import sys
    import io
    
    # Set UTF-8 encoding for console output
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Test simple request first
    print("Testing simple request...")
    out1 = app.invoke(
        {"messages": [{"role": "user", "content": "Hello, tell me about yourself."}]},
        config={"configurable": {"thread_id": "t1"}},
    )
    print("Simple test result:", repr(out1["messages"][-1].content[:100]))
    
    # Test planning tool
    print("\nTesting planning...")
    out2 = app.invoke(
        {"messages": [{"role": "user", "content": "Plan this task: get news about AI, create an image, write a post"}]},
        config={"configurable": {"thread_id": "t2"}},
    )
    print("Planning test result:", repr(out2["messages"][-1].content[:100]))
    
    print("\nSystem ready for web interface testing!")