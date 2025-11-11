"""
AIezzy MCP Server
Exposes AIezzy's AI capabilities through Model Context Protocol (MCP)
"""

from mcp.server.fastmcp import FastMCP
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("AIezzy")

# Import AIezzy modules
import fal_client
fal_client.api_key = os.getenv("FAL_KEY")

# Configure asset directories
ASSETS_DIR = Path("assets")
VIDEOS_DIR = Path("videos")
ASSETS_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)

# ============================================================================
# IMAGE GENERATION TOOLS
# ============================================================================

@mcp.tool()
def generate_image(prompt: str, num_images: int = 1) -> str:
    """
    Generate an image from a text prompt using FAL AI nano-banana.

    Args:
        prompt: Description of the image to generate
        num_images: Number of images to generate (default: 1)

    Returns:
        Path to the generated image file
    """
    import time
    import requests

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
        response = requests.get(image_url)
        if response.status_code == 200:
            timestamp = int(time.time() * 1000000)
            filename = f"img_{timestamp}.png"
            path = ASSETS_DIR / filename

            counter = 1
            while path.exists():
                filename = f"img_{timestamp}_{counter}.png"
                path = ASSETS_DIR / filename
                counter += 1

            path.write_bytes(response.content)
            return f"Image generated successfully: {path}"
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    else:
        raise Exception("Failed to generate image with nano-banana")


@mcp.tool()
def edit_image(image_path: str, prompt: str) -> str:
    """
    Edit an existing image using FAL AI's nano-banana/edit model.

    Args:
        image_path: Path to the image file to edit
        prompt: Description of the desired changes

    Returns:
        Path to the edited image file
    """
    import time
    import requests

    # Upload image to FAL
    image_url = fal_client.upload_file(image_path)

    result = fal_client.subscribe(
        "fal-ai/nano-banana/edit",
        arguments={
            "image_url": image_url,
            "prompt": prompt
        },
        with_logs=True
    )

    if result and result.get('images') and len(result['images']) > 0:
        edited_url = result['images'][0]['url']

        # Download and save edited image
        response = requests.get(edited_url)
        if response.status_code == 200:
            timestamp = int(time.time() * 1000000)
            filename = f"edited_{timestamp}.png"
            path = ASSETS_DIR / filename

            path.write_bytes(response.content)
            return f"Image edited successfully: {path}"
        else:
            raise Exception(f"Failed to download edited image: {response.status_code}")
    else:
        raise Exception("Failed to edit image")

# ============================================================================
# VIDEO GENERATION TOOLS
# ============================================================================

@mcp.tool()
def generate_video_from_text(prompt: str, resolution: str = "720p", aspect_ratio: str = "16:9") -> str:
    """
    Generate a video from a text prompt using FAL AI LTX-Video.

    Args:
        prompt: Description of the video to generate
        resolution: Video resolution (480p, 720p, 1080p)
        aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)

    Returns:
        Path to the generated video file
    """
    import time
    import requests

    # Resolution mapping
    resolution_map = {
        "480p": {"width": 704, "height": 480},
        "720p": {"width": 1024, "height": 576},
        "1080p": {"width": 1216, "height": 832}
    }

    dimensions = resolution_map.get(resolution, resolution_map["720p"])

    result = fal_client.subscribe(
        "fal-ai/ltx-video",
        arguments={
            "prompt": prompt,
            "width": dimensions["width"],
            "height": dimensions["height"],
            "num_frames": 121,
            "num_inference_steps": 30
        },
        with_logs=True
    )

    if result and result.get('video') and result['video'].get('url'):
        video_url = result['video']['url']

        # Download and save video
        response = requests.get(video_url)
        if response.status_code == 200:
            timestamp = int(time.time())
            filename = f"video_{timestamp}.mp4"
            path = VIDEOS_DIR / filename

            path.write_bytes(response.content)
            return f"Video generated successfully: {path}"
        else:
            raise Exception(f"Failed to download video: {response.status_code}")
    else:
        raise Exception("Failed to generate video")


@mcp.tool()
def generate_video_from_image(image_path: str, prompt: str, resolution: str = "720p") -> str:
    """
    Animate an image into a video using FAL AI LTX-Video.

    Args:
        image_path: Path to the image file to animate
        prompt: Description of the animation
        resolution: Video resolution (480p, 720p, 1080p)

    Returns:
        Path to the generated video file
    """
    import time
    import requests

    # Upload image to FAL
    image_url = fal_client.upload_file(image_path)

    resolution_map = {
        "480p": {"width": 704, "height": 480},
        "720p": {"width": 1024, "height": 576},
        "1080p": {"width": 1216, "height": 832}
    }

    dimensions = resolution_map.get(resolution, resolution_map["720p"])

    result = fal_client.subscribe(
        "fal-ai/ltx-video",
        arguments={
            "prompt": prompt,
            "image_url": image_url,
            "width": dimensions["width"],
            "height": dimensions["height"],
            "num_frames": 121,
            "num_inference_steps": 30
        },
        with_logs=True
    )

    if result and result.get('video') and result['video'].get('url'):
        video_url = result['video']['url']

        response = requests.get(video_url)
        if response.status_code == 200:
            timestamp = int(time.time())
            filename = f"video_{timestamp}.mp4"
            path = VIDEOS_DIR / filename

            path.write_bytes(response.content)
            return f"Video from image generated successfully: {path}"
        else:
            raise Exception(f"Failed to download video: {response.status_code}")
    else:
        raise Exception("Failed to generate video from image")

# ============================================================================
# WEB SEARCH TOOL
# ============================================================================

@mcp.tool()
def search_web(query: str) -> str:
    """
    Search the web for current information using Tavily AI.

    Args:
        query: Search query

    Returns:
        Formatted search results with sources
    """
    from tavily import TavilyClient
    from datetime import datetime

    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key:
        return "Web search unavailable: Tavily API key not configured."

    tavily = TavilyClient(api_key=tavily_api_key)
    current_date = datetime.now().strftime("%B %d, %Y")

    search_result = tavily.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True,
        include_raw_content=False,
        include_images=False
    )

    formatted_results = f"**Web Search Results for: '{query}'** *(as of {current_date})*\n\n"

    if search_result.get('answer'):
        formatted_results += f"**Summary:**\n{search_result['answer']}\n\n"

    if search_result.get('results'):
        formatted_results += "**Sources:**\n"
        for i, result in enumerate(search_result['results'][:3], 1):
            title = result.get('title', 'No title')
            content = result.get('content', 'No content available')
            url = result.get('url', '')

            if len(content) > 200:
                content = content[:200] + "..."

            formatted_results += f"\n**{i}. {title}**\n{content}\n"
            if url:
                formatted_results += f"*Source: {url}*\n"

    return formatted_results

# ============================================================================
# TEXT PROCESSING TOOLS
# ============================================================================

@mcp.tool()
def count_words(text: str) -> str:
    """
    Count words, characters, sentences, and paragraphs in text.

    Args:
        text: Text to analyze

    Returns:
        Statistics about the text
    """
    import re

    # Count words
    words = len(re.findall(r'\b\w+\b', text))

    # Count characters (with and without spaces)
    chars_with_spaces = len(text)
    chars_without_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

    # Count sentences (basic - ends with . ! ?)
    sentences = len(re.findall(r'[.!?]+', text))

    # Count paragraphs (separated by blank lines)
    paragraphs = len([p for p in text.split('\n\n') if p.strip()])

    return f"""Text Statistics:
- Words: {words}
- Characters (with spaces): {chars_with_spaces}
- Characters (without spaces): {chars_without_spaces}
- Sentences: {sentences}
- Paragraphs: {paragraphs}"""


@mcp.tool()
def convert_text_case(text: str, case_type: str) -> str:
    """
    Convert text to different cases.

    Args:
        text: Text to convert
        case_type: Type of case (uppercase, lowercase, title, sentence, capitalize)

    Returns:
        Converted text
    """
    if case_type == "uppercase":
        return text.upper()
    elif case_type == "lowercase":
        return text.lower()
    elif case_type == "title":
        return text.title()
    elif case_type == "sentence":
        sentences = text.split('. ')
        return '. '.join(s.capitalize() for s in sentences)
    elif case_type == "capitalize":
        return text.capitalize()
    else:
        return f"Unknown case type: {case_type}"


@mcp.tool()
def generate_password(length: int = 16, include_uppercase: bool = True,
                     include_lowercase: bool = True, include_numbers: bool = True,
                     include_symbols: bool = True) -> str:
    """
    Generate a secure random password.

    Args:
        length: Password length (default: 16)
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_numbers: Include numbers
        include_symbols: Include symbols

    Returns:
        Generated password
    """
    import random
    import string

    chars = ''
    if include_uppercase:
        chars += string.ascii_uppercase
    if include_lowercase:
        chars += string.ascii_lowercase
    if include_numbers:
        chars += string.digits
    if include_symbols:
        chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'

    if not chars:
        return "Error: Must include at least one character type"

    password = ''.join(random.choice(chars) for _ in range(length))
    return f"Generated password: {password}"

# ============================================================================
# QR CODE & BARCODE TOOLS
# ============================================================================

@mcp.tool()
def create_qr_code(data: str, size: int = 10) -> str:
    """
    Generate a QR code for text, URL, or other data.

    Args:
        data: Data to encode in QR code
        size: QR code size (default: 10)

    Returns:
        Path to the generated QR code image
    """
    import qrcode
    import time

    qr = qrcode.QRCode(version=1, box_size=size, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    timestamp = int(time.time() * 1000000)
    filename = f"qr_{timestamp}.png"
    path = ASSETS_DIR / filename

    img.save(str(path))
    return f"QR code generated successfully: {path}"


@mcp.tool()
def create_barcode(data: str, barcode_type: str = 'code128') -> str:
    """
    Generate a barcode image.

    Args:
        data: Data to encode
        barcode_type: Type of barcode (code128, ean13, etc.)

    Returns:
        Path to the generated barcode image
    """
    import barcode
    from barcode.writer import ImageWriter
    import time

    barcode_class = barcode.get_barcode_class(barcode_type)
    barcode_instance = barcode_class(data, writer=ImageWriter())

    timestamp = int(time.time() * 1000000)
    filename = f"barcode_{timestamp}"
    path = ASSETS_DIR / filename

    barcode_instance.save(str(path))
    return f"Barcode generated successfully: {path}.png"


# ============================================================================
# MAIN SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run MCP server with stdio transport
    mcp.run(transport="stdio")
