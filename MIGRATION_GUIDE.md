# Migration Guide: OpenAI to Google Gemini API

## Overview
This guide explains the migration from OpenAI GPT-4/GPT-5 to Google Gemini 2.0 Flash API. The migration provides better performance, cost efficiency, and unified AI provider integration.

## What Changed?

### 1. **Dependencies**
**Removed:**
- `langchain-openai`
- `openai`

**Added:**
- `langchain-google-genai`
- `google-generativeai`

### 2. **Environment Variables**
**Before:**
```env
OPENAI_API_KEY=sk-your-openai-key-here
```

**After:**
```env
GOOGLE_API_KEY=your-google-api-key-here
```

### 3. **Model Replacements**

| Component | Before | After |
|-----------|--------|-------|
| Master Coordinator | GPT-5 | Gemini 2.0 Flash |
| Quick Evaluator | GPT-5-mini | Gemini 2.0 Flash |
| Vision Analysis | GPT-5 Vision | Gemini 2.0 Flash Vision |
| Text Extraction (OCR) | GPT-5 Vision | Gemini 2.0 Flash Vision |

## Migration Steps

### Step 1: Get Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### Step 2: Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

This will automatically install the new Gemini packages and remove unused OpenAI dependencies.

### Step 3: Update Environment Variables
1. Open your `.env` file
2. Remove the line: `OPENAI_API_KEY=...`
3. Add the line: `GOOGLE_API_KEY=your_google_api_key_here`
4. Replace `your_google_api_key_here` with your actual API key

### Step 4: Restart the Application
```bash
python web_app.py
```

## Testing Checklist

After migration, test the following features:

- [ ] **Text Chat**: Send a simple message like "Hello, how are you?"
- [ ] **Image Analysis**: Upload an image and ask "What's in this image?"
- [ ] **Image Generation**: Request "Generate an image of a sunset"
- [ ] **Image Editing**: Upload an image and say "Make it black and white"
- [ ] **PDF Text Extraction**: Upload a PDF and ask "Extract text from this"
- [ ] **Multi-Image Fusion**: Upload 2+ images and say "Combine these images"
- [ ] **Video Generation**: Request "Create a video of waves"
- [ ] **Web Search**: Ask "What's the latest news about AI?"

## Benefits of Gemini Migration

### 1. **Cost Efficiency**
- Gemini 2.0 Flash is more cost-effective than GPT-4/5
- Lower API costs for vision and text operations
- Free tier available for testing and development

### 2. **Performance**
- Faster inference times with Gemini 2.0 Flash
- Native multimodal capabilities (text + vision in one model)
- Improved vision understanding and OCR accuracy

### 3. **Unified Provider**
- Single AI provider (Google) for all LLM operations
- Simplified API key management
- Consistent billing and usage tracking

### 4. **Future-Proof**
- Access to Google's latest AI innovations
- Regular model updates and improvements
- Growing ecosystem of Gemini-powered tools

## Troubleshooting

### Issue: "API key not found" error
**Solution:** Ensure `GOOGLE_API_KEY` is set in your `.env` file and the file is in the project root directory.

### Issue: "Model not found" error
**Solution:** The Gemini 2.0 Flash Experimental model may have naming changes. Check [Google's documentation](https://ai.google.dev/models/gemini) for the latest model names.

### Issue: Vision analysis not working
**Solution:** Ensure the image format is supported (JPEG, PNG, WebP, GIF). Try with a different image.

### Issue: Rate limit errors
**Solution:** Gemini has rate limits based on your API tier. Check your [Google Cloud Console](https://console.cloud.google.com/) for quota information.

## API Key Management

### Free Tier Limits
- **Gemini 2.0 Flash**: 15 requests per minute (RPM), 1 million tokens per minute (TPM)
- **Vision**: Same limits as text

### Upgrading
To increase limits:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable billing for your project
3. Request quota increases if needed

## Rollback Instructions

If you need to rollback to OpenAI:

1. Reinstall old dependencies:
   ```bash
   pip install langchain-openai openai
   pip uninstall langchain-google-genai google-generativeai
   ```

2. Revert code changes using git:
   ```bash
   git checkout HEAD~1 app.py requirements.txt
   ```

3. Update `.env`:
   ```env
   OPENAI_API_KEY=sk-your-openai-key-here
   ```

## Support

### Getting Help
- **Gemini Documentation**: https://ai.google.dev/docs
- **AIezzy Issues**: https://github.com/yatendra3192/aiezzy-ai-chatbot/issues
- **Google AI Studio**: https://aistudio.google.com/

### Common Questions

**Q: Will my old conversations work?**
A: Yes! All conversation history is preserved. Only the AI model backend has changed.

**Q: Do I need to update my Railway deployment?**
A: Yes, update the `GOOGLE_API_KEY` environment variable in your Railway dashboard and remove `OPENAI_API_KEY`.

**Q: Is Gemini as good as GPT-4?**
A: Gemini 2.0 Flash offers comparable or better performance for most tasks, with significantly faster inference and lower costs.

## Version History

- **Phase 13 (November 19, 2025)**: Complete migration to Google Gemini API
- **Phase 12 (August 27, 2025)**: Migrated image generation to FAL AI nano-banana (Gemini-powered)
- **Phase 8 (August 23, 2025)**: Fixed OpenAI deprecation warnings

---

**Last Updated**: November 19, 2025
**Migration Status**: Complete ✅
**Production Deployment**: Ready for aiezzy.com
