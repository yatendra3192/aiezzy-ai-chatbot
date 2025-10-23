"""
Image Conversion & Processing Module
Provides tools for converting between image formats and image manipulation
"""

import os
import pathlib
from PIL import Image
from typing import Tuple

# Setup directories
DATA_DIR = os.getenv('RAILWAY_VOLUME_MOUNT_PATH', os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(DATA_DIR, 'assets')

# Ensure directory exists
os.makedirs(ASSETS_DIR, exist_ok=True)


# ==================== FILE PATH NORMALIZATION ====================

def normalize_file_path(file_path: str) -> str:
    """
    Normalize file paths to handle various input formats:
    - Full absolute paths: /app/data/assets/image.jpg
    - Relative paths: assets/image.jpg
    - Just filenames: image.jpg
    - Web URLs: /assets/image.jpg

    Returns the full absolute path if file exists, otherwise raises FileNotFoundError.
    """
    if not file_path:
        raise FileNotFoundError("No file path provided")

    # Remove web URL prefix if present
    if file_path.startswith('/documents/'):
        file_path = file_path.replace('/documents/', '')
    elif file_path.startswith('/assets/'):
        file_path = file_path.replace('/assets/', '')
    elif file_path.startswith('/uploads/'):
        file_path = file_path.replace('/uploads/', '')

    # Case 1: Already a valid absolute path
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path

    # Case 2: Check in ASSETS_DIR (primary location for images)
    assets_path = os.path.join(ASSETS_DIR, os.path.basename(file_path))
    if os.path.exists(assets_path):
        return assets_path

    # Case 3: Check in parent directory's uploads folder
    uploads_dir = os.path.join(os.path.dirname(ASSETS_DIR), 'uploads')
    uploads_path = os.path.join(uploads_dir, os.path.basename(file_path))
    if os.path.exists(uploads_path):
        return uploads_path

    # Case 4: Check in parent directory's documents folder (some images might be there)
    documents_dir = os.path.join(os.path.dirname(ASSETS_DIR), 'documents')
    documents_path = os.path.join(documents_dir, os.path.basename(file_path))
    if os.path.exists(documents_path):
        return documents_path

    # Case 5: Check relative to current directory
    if os.path.exists(file_path):
        return os.path.abspath(file_path)

    # File not found in any location
    raise FileNotFoundError(f"Image file not found: {file_path}. Searched in: {ASSETS_DIR}, {uploads_dir}, {documents_dir}, and current directory.")


# ==================== JPEG to PNG ====================

def jpeg_to_png(input_path: str, output_name: str = None) -> str:
    """
    Convert JPEG image to PNG format

    Args:
        input_path: Path to JPEG file
        output_name: Optional output filename

    Returns:
        Path to generated PNG file
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"JPEG file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.png"

        if not output_name.endswith('.png'):
            output_name += '.png'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)

        # Convert RGBA to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            # Keep transparency for PNG
            img.save(output_path, 'PNG')
        else:
            img.save(output_path, 'PNG')

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert JPEG to PNG: {str(e)}")


# ==================== PNG to JPEG ====================

def png_to_jpeg(input_path: str, output_name: str = None, quality: int = 95) -> str:
    """
    Convert PNG image to JPEG format

    Args:
        input_path: Path to PNG file
        output_name: Optional output filename
        quality: JPEG quality (1-100, default 95)

    Returns:
        Path to generated JPEG file
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"PNG file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.jpg"

        if not output_name.lower().endswith(('.jpg', '.jpeg')):
            output_name += '.jpg'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)

        # Convert RGBA to RGB (JPEG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, 'JPEG', quality=quality, optimize=True)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert PNG to JPEG: {str(e)}")


# ==================== WEBP to PNG ====================

def webp_to_png(input_path: str, output_name: str = None) -> str:
    """
    Convert WEBP image to PNG format

    Args:
        input_path: Path to WEBP file
        output_name: Optional output filename

    Returns:
        Path to generated PNG file
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"WEBP file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.png"

        if not output_name.endswith('.png'):
            output_name += '.png'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)
        img.save(output_path, 'PNG')

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert WEBP to PNG: {str(e)}")


# ==================== WEBP to JPEG ====================

def webp_to_jpeg(input_path: str, output_name: str = None, quality: int = 95) -> str:
    """
    Convert WEBP image to JPEG format

    Args:
        input_path: Path to WEBP file
        output_name: Optional output filename
        quality: JPEG quality (1-100, default 95)

    Returns:
        Path to generated JPEG file
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"WEBP file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.jpg"

        if not output_name.lower().endswith(('.jpg', '.jpeg')):
            output_name += '.jpg'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)

        # Convert to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, 'JPEG', quality=quality, optimize=True)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert WEBP to JPEG: {str(e)}")


# ==================== HEIC to JPEG ====================

def heic_to_jpeg(input_path: str, output_name: str = None, quality: int = 95) -> str:
    """
    Convert HEIC/HEIF image to JPEG format (iOS photos)

    Args:
        input_path: Path to HEIC file
        output_name: Optional output filename
        quality: JPEG quality (1-100, default 95)

    Returns:
        Path to generated JPEG file
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        # Try to import pillow-heif
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            raise Exception("pillow-heif library not installed. Run: pip install pillow-heif")

        if not os.path.exists(input_path):
            raise Exception(f"HEIC file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.jpg"

        if not output_name.lower().endswith(('.jpg', '.jpeg')):
            output_name += '.jpg'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(output_path, 'JPEG', quality=quality, optimize=True)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert HEIC to JPEG: {str(e)}")


# ==================== GIF to PNG ====================

def gif_to_png(input_path: str, output_name: str = None, extract_all_frames: bool = False) -> str:
    """
    Convert GIF to PNG (first frame or all frames)

    Args:
        input_path: Path to GIF file
        output_name: Optional output filename
        extract_all_frames: If True, extract all frames as separate PNGs

    Returns:
        Path to generated PNG file (or first file if multiple frames)
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"GIF file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            output_name = f"{input_name}_converted.png"

        if not output_name.endswith('.png'):
            output_name += '.png'

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open GIF
        img = Image.open(input_path)

        if not extract_all_frames:
            # Extract first frame only
            img.save(output_path, 'PNG')
            return output_path
        else:
            # Extract all frames
            frame_paths = []
            frame_count = 0

            try:
                while True:
                    frame_name = f"{pathlib.Path(output_name).stem}_frame_{frame_count}.png"
                    frame_path = os.path.join(ASSETS_DIR, frame_name)
                    img.save(frame_path, 'PNG')
                    frame_paths.append(frame_path)
                    frame_count += 1
                    img.seek(img.tell() + 1)
            except EOFError:
                pass  # End of frames

            return frame_paths[0] if frame_paths else output_path

    except Exception as e:
        raise Exception(f"Failed to convert GIF to PNG: {str(e)}")


# ==================== Resize Image ====================

def resize_image(input_path: str, width: int = None, height: int = None,
                output_name: str = None, maintain_aspect: bool = True) -> str:
    """
    Resize image to specified dimensions

    Args:
        input_path: Path to image file
        width: Target width (optional)
        height: Target height (optional)
        output_name: Optional output filename
        maintain_aspect: Keep aspect ratio (default True)

    Returns:
        Path to resized image
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"Image file not found: {input_path}")

        if not width and not height:
            raise Exception("Must specify at least width or height")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            ext = pathlib.Path(input_path).suffix
            output_name = f"{input_name}_resized{ext}"

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open image
        img = Image.open(input_path)
        original_width, original_height = img.size

        # Calculate dimensions
        if maintain_aspect:
            if width and not height:
                # Calculate height based on width
                aspect_ratio = original_height / original_width
                height = int(width * aspect_ratio)
            elif height and not width:
                # Calculate width based on height
                aspect_ratio = original_width / original_height
                width = int(height * aspect_ratio)
            else:
                # Both specified - use smaller scaling factor
                width_ratio = width / original_width
                height_ratio = height / original_height
                if width_ratio < height_ratio:
                    height = int(original_height * width_ratio)
                else:
                    width = int(original_width * height_ratio)
        else:
            # Use specified dimensions or keep original
            width = width or original_width
            height = height or original_height

        # Resize
        resized = img.resize((width, height), Image.Resampling.LANCZOS)

        # Save with appropriate format
        if img.format:
            resized.save(output_path, img.format)
        else:
            # Determine format from extension
            ext = pathlib.Path(output_name).suffix.lower()
            format_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG',
                         '.webp': 'WEBP', '.gif': 'GIF', '.bmp': 'BMP'}
            img_format = format_map.get(ext, 'PNG')
            if img_format == 'JPEG' and resized.mode in ('RGBA', 'LA', 'P'):
                resized = resized.convert('RGB')
            resized.save(output_path, img_format)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to resize image: {str(e)}")


# ==================== Compress Image ====================

def compress_image(input_path: str, output_name: str = None,
                  quality: int = 85, optimization: str = 'medium') -> str:
    """
    Compress image to reduce file size

    Args:
        input_path: Path to image file
        output_name: Optional output filename
        quality: Compression quality (1-100, default 85)
        optimization: 'low', 'medium', or 'high' (default 'medium')

    Returns:
        Path to compressed image
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"Image file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            ext = pathlib.Path(input_path).suffix
            output_name = f"{input_name}_compressed{ext}"

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Quality settings based on optimization level
        quality_map = {
            'low': quality,
            'medium': min(quality - 10, 75),
            'high': min(quality - 20, 60)
        }

        final_quality = quality_map.get(optimization, quality)

        # Open image
        img = Image.open(input_path)

        # Convert format if needed
        img_format = img.format or 'JPEG'

        if img_format == 'JPEG' or pathlib.Path(output_name).suffix.lower() in ('.jpg', '.jpeg'):
            # JPEG compression
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=final_quality, optimize=True)
        elif img_format == 'PNG' or pathlib.Path(output_name).suffix.lower() == '.png':
            # PNG compression
            img.save(output_path, 'PNG', optimize=True)
        elif img_format == 'WEBP' or pathlib.Path(output_name).suffix.lower() == '.webp':
            # WEBP compression
            img.save(output_path, 'WEBP', quality=final_quality, optimize=True)
        else:
            # Default to original format
            img.save(output_path, img_format, quality=final_quality, optimize=True)

        # Get file size reduction
        original_size = os.path.getsize(input_path) / 1024  # KB
        compressed_size = os.path.getsize(output_path) / 1024  # KB
        reduction = ((original_size - compressed_size) / original_size) * 100

        print(f"Compressed from {original_size:.1f}KB to {compressed_size:.1f}KB ({reduction:.1f}% reduction)")

        return output_path

    except Exception as e:
        raise Exception(f"Failed to compress image: {str(e)}")


# ==================== Convert to Grayscale ====================

def convert_to_grayscale(input_path: str, output_name: str = None) -> str:
    """
    Convert image to grayscale (black and white)

    Args:
        input_path: Path to image file
        output_name: Optional output filename

    Returns:
        Path to grayscale image
    """
    try:
        if not os.path.exists(input_path):
            raise Exception(f"Image file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            ext = pathlib.Path(input_path).suffix
            output_name = f"{input_name}_grayscale{ext}"

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and convert
        img = Image.open(input_path)
        grayscale = img.convert('L')

        # Save with appropriate format
        img_format = img.format or 'PNG'
        grayscale.save(output_path, img_format)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to convert to grayscale: {str(e)}")


# ==================== Rotate Image ====================

def rotate_image(input_path: str, angle: int = 90, output_name: str = None,
                expand: bool = True) -> str:
    """
    Rotate image by specified angle

    Args:
        input_path: Path to image file
        angle: Rotation angle in degrees (positive = counter-clockwise)
        output_name: Optional output filename
        expand: Expand canvas to fit rotated image (default True)

    Returns:
        Path to rotated image
    """
    try:
        # Normalize file path
        input_path = normalize_file_path(input_path)

        if not os.path.exists(input_path):
            raise Exception(f"Image file not found: {input_path}")

        # Generate output name if not provided
        if not output_name:
            input_name = pathlib.Path(input_path).stem
            ext = pathlib.Path(input_path).suffix
            output_name = f"{input_name}_rotated{ext}"

        output_path = os.path.join(ASSETS_DIR, output_name)

        # Open and rotate
        img = Image.open(input_path)
        rotated = img.rotate(angle, expand=expand)

        # Save with appropriate format
        img_format = img.format or 'PNG'
        if img_format == 'JPEG' and rotated.mode in ('RGBA', 'LA', 'P'):
            rotated = rotated.convert('RGB')
        rotated.save(output_path, img_format)

        return output_path

    except Exception as e:
        raise Exception(f"Failed to rotate image: {str(e)}")
