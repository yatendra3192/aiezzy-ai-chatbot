# AIezzy - LangGraph Multi-Agent Web App

A production-ready ChatGPT-style web application featuring advanced LangGraph multi-agent AI with comprehensive multimedia capabilities including vision analysis, image generation, image editing, video generation, multi-image fusion, web search, and intelligent conversation management.

**🌐 Live at: [aiezzy.com](https://aiezzy.com)**

## 🆕 Latest Updates (August 23, 2025)

### ✅ Bug Fixes & Improvements
- **Fixed Recursion Limit Error**: Resolved infinite loop issues with proper stop conditions
- **Updated Deprecated Imports**: Fixed LangChain compatibility issues
- **Enhanced Multi-Image Workflow**: Now automatically accesses generated images from conversation history
- **Improved Context Management**: Better thread isolation and image context handling
- **Optimized Agent Coordination**: Reduced tool calling loops and improved response accuracy
- **Added Loading Animations**: Beautiful loading indicators eliminate blank screen during processing
- **Enhanced UX**: Spinning animations, context-aware messages, and input disabling during requests
- **Fixed Multi-Step Workflow**: Resolved intermittent failures in complex multi-step tasks
- **Context Isolation**: Eliminated image contamination between conversations and requests

## ✨ Features

### 🤖 **Enhanced Multi-Agent Architecture**
- **Master Coordinator Agent**: Unified intelligent orchestration using GPT-4o
- **Vision Analyst Agent**: Analyzes images and provides detailed descriptions using GPT-4o
- **Image Generator Agent**: Creates high-quality images from text prompts using OpenAI gpt-image-1
- **Image Editor Agent**: Edits existing images using FAL AI flux-kontext model
- **Video Generator Agent**: Creates videos from text using FAL AI LTX-Video-13B
- **Image Animator Agent**: Animates static images into videos using FAL AI LTX-Video-13B
- **Multi-Image Fusion Agent**: Combines multiple images using FAL AI FLUX Pro Kontext Multi
- **Web Search Agent**: Searches the web for current events, news, and real-time information using Tavily AI
- **Intelligent Task Coordination**: Automatically plans and executes complex multi-step requests

### 👁️ **Advanced Vision Analysis**
- Upload images for detailed AI analysis and description
- Ask specific questions about image content
- Supports PNG, JPG, JPEG, GIF, WEBP formats
- Preserves image context for follow-up conversations
- Multi-image context tracking for fusion operations

### 🎨 **Comprehensive Image Capabilities**
- **Generation**: Create custom images from text descriptions using gpt-image-1
- **Editing**: Modify existing images with AI-powered editing (add text, change backgrounds, etc.)
- **Multi-Image Fusion**: Combine 2-5 uploaded images into artistic compositions using FLUX Pro
- **High Quality**: Supports various sizes and quality settings
- **Preview & Modal**: Full-size image viewing with click-to-expand functionality
- **Simplified Upload**: One-click upload for any number of images (1-5) with intelligent routing
- **Smart Display**: All uploaded images show properly in chat messages with optimized sizing

### 🎬 **Video Generation & Animation**
- **Text-to-Video**: Create high-quality videos from detailed text descriptions
- **Image-to-Video**: Animate uploaded static images into dynamic videos
- **Professional Quality**: 720p resolution, 30fps, customizable frame counts
- **HTML5 Player**: Embedded video controls with responsive design
- **Local Storage**: Videos saved locally and served efficiently
- **Cinematic Options**: Support for various aspect ratios and video lengths

### 🔍 **Web Search & Real-Time Information**
- **Current Events**: Search for latest news and current events powered by Tavily AI
- **AI-Generated Summaries**: Provides concise answers along with source material
- **Smart Routing**: Automatically detects when web search is needed
- **Reliable Sources**: Focuses on credible and recent information
- **Agent-Optimized**: Uses Tavily's API specifically designed for AI agents

### 💬 **Modern Chat Interface with Progress Feedback**
- **ChatGPT-Style UI**: Clean, modern interface matching ChatGPT's design
- **Real-Time Progress Indicators**: Visual feedback for long-running multi-step operations
- **Step-by-Step Visualization**: Shows current activity and completed tasks
- **Progress Bars**: Visual completion percentage for complex requests
- **Recent Chats**: Sidebar with conversation history and management
- **Conversation Management**: Switch between multiple chat sessions seamlessly
- **Auto-Save**: Conversations automatically saved to localStorage with media preservation
- **Message Formatting**: Proper markdown rendering for AI responses
- **Enhanced Media Display**: Images and videos persist after browser refresh

### 📱 **Recent Chats System**
- **Conversation History**: Automatic saving and loading of chat sessions with multimedia
- **Smart Titles**: Auto-generated titles based on first user message
- **Time Stamps**: Relative time display (Now, 5m, 2h, 3d)
- **Delete Management**: Hover-to-reveal delete buttons for chat cleanup
- **Active State**: Visual indication of currently selected conversation
- **Persistent Storage**: All conversations and media restored between browser sessions

### ⚡ **Real-Time Progress System**
- **Multi-Step Detection**: Automatically identifies complex requests
- **Progress Visualization**: Step-by-step execution with visual indicators
- **Time Estimates**: Realistic completion time predictions
- **Status Updates**: Real-time messages about current activities
- **No Blank Screens**: Users always see what's happening during processing
- **Professional Feedback**: Eliminates confusion during long operations

### 📤 **Simplified Upload Experience**
- **One-Click Multi-Upload**: Select 1-5 images with single attachment button
- **No Complex Dialogs**: Removed confusing popup choices between single/multi modes
- **Intelligent Agent Routing**: AI automatically decides operation based on:
  - Image count (1 vs 2+ images)
  - User prompt keywords (edit, animate, combine, analyze)
- **Perfect Display**: All uploaded images show properly in chat messages
- **Optimized Previews**: Properly sized thumbnails (80x80px) with numbered indicators
- **Smart Defaults**: Sensible default prompts when no message provided

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Create/edit `.env` file with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here    # Get from https://platform.openai.com/api-keys
FAL_KEY=your_fal_ai_key_here               # Get from https://www.fal.ai/
TAVILY_API_KEY=your_tavily_api_key_here    # Get from https://tavily.com/
```

**API Key Sources:**
- **OpenAI**: Required for GPT-4o vision analysis and image generation
- **FAL AI**: Required for image editing, video generation, and multi-image fusion
- **Tavily AI**: Required for web search functionality (agent-optimized)

### 3. Run the Application

**Web Interface (Recommended):**
```bash
python web_app.py
```
Then open http://localhost:5000 in your browser.

**Command Line Testing:**
```bash
python app.py
```

## 🎯 Usage Guide

### Web Interface Features
1. **Text Chat**: Ask questions, request explanations, or have conversations
2. **Image Analysis**: Upload images and ask "What do you see?" or specific questions
3. **Image Generation**: Request "Create a logo for..." or "Generate an image of..."
4. **Image Editing**: Upload an image and ask to "Add text to this image" or "Change the background"
5. **Video Generation**: Request "Create a video of..." or "Generate a video showing..."
6. **Image Animation**: Upload an image and ask to "Animate this image" or "Make this picture move"
7. **Multi-Image Fusion**: Upload multiple images and request "Combine these images" or "Merge these photos"
8. **Web Search**: Ask "What are the latest..." or "Current news about..."
9. **Multi-Step Workflows**: Complex requests like "Get news, create a video, write a post"
10. **Conversation Management**: 
    - Click "New chat" to start fresh conversations
    - Click any item in "Recent Chats" to switch conversations
    - Hover over chat items to delete unwanted conversations

### Example Prompts

#### **Single-Task Examples**
- **Vision**: "What's in this image?" (with uploaded image)
- **Generation**: "Create a modern logo for a tech startup"
- **Editing**: "Add the text 'Hello World' to the bottom right corner" (with uploaded image)
- **Video Creation**: "Create a video of a sunset over mountains"
- **Image Animation**: "Animate this portrait with gentle movement" (with uploaded image)
- **Multi-Image**: "Combine these two photos into one artistic composition" (with 2+ uploaded images)
- **Web Search**: "What are the latest AI developments this week?"

#### **Multi-Step Workflow Examples**
- **News + Video + Post**: "Get latest news from Mumbai, create a video about it, write a LinkedIn post"
- **Search + Image + Content**: "Find trending tech news, generate a related image, compose a social media post"
- **Analysis + Animation + Description**: "Analyze this image, animate it, and write a description"

## 🛠️ API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Modern chat interface with progress indicators |
| `/api/chat` | POST | Multi-agent conversations with progress tracking |
| `/api/analyze-image` | POST | Image upload and analysis with context preservation |
| `/assets/<filename>` | GET | Serve generated/edited/multi images |
| `/videos/<filename>` | GET | Serve generated video files |

## 🏗️ Enhanced Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Modern Chat UI │────│   Flask Server   │────│ LangGraph App   │
│ (ChatGPT-style  │    │  (progress       │    │ (coordinator)   │
│  + Progress)    │    │   tracking)      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
        ┌────────────────────────────────────────────────┼─────────────────────────────────────┐
        │            │            │           │           │           │            │            │
┌───────▼────┐ ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐ ┌──▼───┐ ┌────▼─────┐ ┌────▼─────┐ ┌───▼────┐
│   Vision   │ │   Image   │ │  Image │ │   Video  │ │Video │ │Multi-Image│ │   Web    │ │External│
│  Analysis  │ │Generation │ │Editing │ │Generation│ │Anim. │ │  Fusion   │ │  Search  │ │  APIs  │
│  (GPT-4o)  │ │(gpt-img-1)│ │(FAL AI)│ │(LTX-13B) │ │(LTX) │ │(FLUX Pro) │ │(Tavily)  │ │        │
└────────────┘ └───────────┘ └────────┘ └──────────┘ └──────┘ └───────────┘ └──────────┘ └────────┘
```

## 📁 Project Structure

```
├── app.py                 # Enhanced LangGraph coordinator with intelligent routing
├── web_app.py            # Flask server with UNIFIED image upload endpoint
├── requirements.txt      # Python dependencies (includes video libraries)
├── .env                  # Environment variables (all API keys)
├── templates/
│   └── modern_chat.html  # Simplified ChatGPT-style interface (no popups)
├── assets/               # Generated, edited, and multi-fusion images
├── videos/               # Generated video files
├── uploads/              # Temporary uploaded image files
├── README.md            # This comprehensive documentation
└── CLAUDE.md            # Detailed development context and history
```

## 🔧 Technical Details

### Models & APIs Used
- **GPT-4o**: Vision analysis, general conversation, and coordination
- **OpenAI gpt-image-1**: High-quality image generation
- **FAL AI flux-kontext**: Advanced image editing capabilities
- **FAL AI LTX-Video-13B**: Professional video generation from text
- **FAL AI LTX-Video-13B Image-to-Video**: Image animation capabilities
- **FAL AI FLUX Pro Kontext Multi**: Multi-image composition and fusion
- **Tavily AI**: Real-time web search optimized for AI agents

### Key Dependencies
- **LangGraph**: Multi-agent orchestration and coordination
- **LangChain**: AI model integration and tool management
- **Flask**: Web framework with multimedia serving
- **OpenAI**: GPT models and image generation
- **FAL Client**: Image editing, video generation, and multi-image fusion
- **Tavily Python**: Real-time web search capabilities

### Data Storage
- **Conversations**: Browser localStorage (JSON format with HTML preservation)
- **Images**: Local filesystem in `/assets` and `/uploads` directories
- **Videos**: Local filesystem in `/videos` directory
- **Session Management**: In-memory for active conversations with context tracking
- **Multi-Image Context**: Last 5 uploaded images maintained for fusion operations

## 🚨 Current Status

### ✅ Completed Features
- **Enhanced LangGraph architecture** with unified coordinator
- **Modern ChatGPT-style interface** with real-time progress indicators
- **Vision analysis** with image upload and context preservation
- **Image generation** via OpenAI gpt-image-1
- **Image editing** via FAL AI flux-kontext
- **Video generation** via FAL AI LTX-Video-13B (text-to-video)
- **Image animation** via FAL AI LTX-Video-13B (image-to-video)
- **Multi-image fusion** via FAL AI FLUX Pro Kontext Multi
- **Web search** via Tavily AI for real-time information
- **Complete conversation management** with media persistence
- **Recent chats sidebar** with enhanced multimedia history
- **Auto-generated conversation titles**
- **Delete conversation functionality**
- **Persistent storage** across sessions with HTML formatting
- **Real-time progress feedback** for multi-step operations
- **Smart task coordination** and sequential execution

### 🔄 Known Issues
- Multi-image generation limited to last 5 uploaded images per session
- Video generation takes 60-120 seconds (inherent to AI video models)
- Large video files may impact browser performance over time
- No user authentication (single-user application)
- No cloud backup for generated videos and images

### 🎯 Potential Enhancements
- **Media Management**: Search functionality for chat history with media
- **Export**: Export conversations with embedded videos to various formats
- **Cloud Integration**: User authentication and cloud storage for media
- **Advanced Video**: Video editing, trimming, and quality controls
- **Batch Operations**: Multiple image upload interface
- **Real-time Streaming**: WebSocket-based progress updates
- **Mobile Optimization**: Touch-friendly video and image controls
- **3D Content**: Integration with 3D model generation
- **Audio**: Speech-to-text and text-to-speech capabilities

## 🏃‍♂️ Quick Start

1. Clone/download the project
2. Install dependencies: `pip install -r requirements.txt`
3. Add API keys to `.env` file (OpenAI, FAL AI, Tavily AI)
4. Run: `python web_app.py`
5. Open: http://localhost:5000
6. Start chatting, uploading images, generating videos, or creating multimedia content!

## 🎮 Usage Examples

### **Simple Operations**
```
"Create a modern logo"                    → Image generation
"Animate this image"                      → Image-to-video (with upload)
"What's happening in tech news today?"    → Web search
"Create a video of ocean waves"           → Text-to-video
"Edit this image to add my name"          → Image editing (with upload)
```

### **Simplified Multi-Image Operations**
```
1. Click attachment → Select 2-5 images at once
2. Type: "Combine these images into one artistic piece" 
   → Agent automatically uses multi-image fusion
3. OR: "blend these with a sunset background"
   → Agent intelligently adapts the fusion
```

### **Complex Multi-Step Workflows**
```
"Get latest news from India, create a video about it, write a LinkedIn post"
↓
Step 1: Web search for Indian news
Step 2: Generate video based on news content
Step 3: Write LinkedIn post incorporating both results
```

### **Advanced Combinations**
```
"Find trending AI news, create an image representing it, then animate that image"
↓ 
Step 1: Search for AI news
Step 2: Generate relevant image
Step 3: Animate the generated image into video
```

## 🎯 Real-Time Progress System

### **Progress Indicators**
- **Smart Detection**: Automatically recognizes multi-step requests
- **Visual Feedback**: Progress bars and step indicators
- **Time Estimates**: Realistic completion time predictions
- **Status Updates**: Live messages about current activities
- **Professional UI**: Eliminates "blank screen" confusion

### **Supported Operations**
- 🔍 **Web Search**: "Searching for latest news..."
- 🎨 **Image Generation**: "Generating custom image..."
- 🎬 **Video Creation**: "Generating custom video..."
- 🔀 **Multi-Image Fusion**: "Combining multiple images..."
- ✏️ **Image Editing**: "Editing image..."
- 📝 **Content Writing**: "Writing LinkedIn post..."

## 🔄 Latest Updates (August 17, 2025)

### **Multi-Image Bug Fixes & System Stability**
- **THREAD CONTEXT ISOLATION**: Fixed critical bug where agent received wrong thread ID (`default` instead of actual)
- **MULTI-IMAGE DETECTION**: Resolved "no images detected" error by adding global thread ID fallback
- **PERSISTENCE FIXES**: Enhanced conversation storage to properly save/restore `imagePaths` array
- **DISPLAY RESTORATION**: Fixed multi-image display when switching between conversations
- **VARIABLE SCOPE**: Resolved `set_recent_image_path` import scope error causing runtime crashes
- **CONVERSATION STORAGE**: Improved multi-image data saving and restoration logic
- **END-TO-END WORKFLOW**: Complete multi-image fusion now fully functional

### **Previous Simplified Upload System (August 16, 2025)**
- **UNIFIED**: Single `/api/analyze-image` endpoint handles all image scenarios (1-5 images)
- **INTELLIGENT**: Agent automatically routes based on image count and prompt context:
  ```
  1 image + "edit the hair color" → Image editing
  1 image + "make it move"       → Video animation  
  1 image + "what's this?"       → Vision analysis
  2+ images + any prompt         → Multi-image fusion
  ```
- **STREAMLINED**: One-click upload with smart AI decision making

### **Technical Improvements Made**
- **app.py**: Added global thread ID fallback in `generate_image_from_multiple` tool (lines 457-459)
- **web_app.py**: Enhanced multi-image context setup with proper debug logging (lines 288-302)
- **modern_chat.html**: 
  - Removed localStorage clearing that prevented persistence (line 2298)
  - Enhanced multi-image restoration logic for conversation switching (lines 2139-2153)
  - Fixed conversation saving to handle `imagePaths` array (lines 2000-2012)
  - Added debug logging for troubleshooting image restoration
- **Bug Resolution**: Fixed all thread context isolation and persistence issues

### **System Reliability**
- **Thread Safety**: Proper isolation between conversation contexts
- **Multi-Image Support**: Complete workflow from upload → detection → fusion → persistence
- **Error Handling**: Resolved all variable scope and import issues
- **Testing Verified**: All multimedia capabilities confirmed working

## 📞 Support

For issues or enhancements, check the conversation history in Recent Chats or start a new conversation to continue development work.

---

**Last Updated**: August 17, 2025  
**Latest**: Multi-image bug fixes - thread context isolation and persistence issues resolved ✅  
**Status**: Production Ready with fully functional multi-image fusion and stable architecture  
**Interface**: Advanced ChatGPT-style UI with bulletproof multi-image support and smart AI decisions