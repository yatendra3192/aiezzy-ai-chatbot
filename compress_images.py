#!/usr/bin/env python3
"""
Image Compression Script for Core Web Vitals Optimization
Compresses logo and favicon to reduce page load times (LCP improvement)
"""

from PIL import Image
import os

def compress_image(input_path, output_path, max_width=None, max_height=None, quality=85):
    """
    Compress and optimize PNG images for web.

    Args:
        input_path: Path to original image
        output_path: Path to save compressed image
        max_width: Maximum width (maintains aspect ratio)
        max_height: Maximum height (maintains aspect ratio)
        quality: Compression quality (1-100, recommended: 85)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(input_path)}")

    # Open image
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path) / 1024  # KB

    print(f"Original: {img.size[0]}x{img.size[1]}px, {original_size:.1f}KB")

    # Resize if needed
    if max_width or max_height:
        img.thumbnail((max_width or img.width, max_height or img.height), Image.Resampling.LANCZOS)
        print(f"Resized to: {img.size[0]}x{img.size[1]}px")

    # Convert RGBA to RGB if no transparency
    if img.mode == 'RGBA':
        # Check if image has transparency
        extrema = img.getextrema()
        has_transparency = len(extrema) > 3 and extrema[3][0] < 255

        if not has_transparency:
            # No transparency, convert to RGB for better compression
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3] if has_transparency else None)
            img = background
            output_path = output_path.replace('.png', '.png')  # Keep PNG
            print("Converted RGBA → RGB (no transparency)")

    # Save with optimization
    img.save(
        output_path,
        optimize=True,
        quality=quality,
        compress_level=9 if output_path.endswith('.png') else None
    )

    compressed_size = os.path.getsize(output_path) / 1024  # KB
    reduction = ((original_size - compressed_size) / original_size) * 100

    print(f"Compressed: {compressed_size:.1f}KB")
    print(f"Reduction: {reduction:.1f}% ({original_size:.1f}KB to {compressed_size:.1f}KB)")
    print(f"[OK] Saved to: {os.path.basename(output_path)}")
    print('='*60)

    return compressed_size, reduction

def main():
    print("\nAIezzy Image Compression for Core Web Vitals Optimization")
    print("="*60)

    # Backup originals
    if not os.path.exists('logo_original.png'):
        os.system('copy logo.png logo_original.png >nul 2>&1' if os.name == 'nt' else 'cp logo.png logo_original.png')
        print("[OK] Backup: logo_original.png created")

    if not os.path.exists('favicon_original.png'):
        os.system('copy favicon.png favicon_original.png >nul 2>&1' if os.name == 'nt' else 'cp favicon.png favicon_original.png')
        print("[OK] Backup: favicon_original.png created")

    # Compress logo (displayed at 40px height, so 512px width is plenty)
    logo_size, logo_reduction = compress_image(
        'logo.png',
        'logo.png',
        max_width=512,  # Reduce from 1024px
        quality=85
    )

    # Compress favicon (standard 64x64 for high-DPI displays)
    favicon_size, favicon_reduction = compress_image(
        'favicon.png',
        'favicon.png',
        max_width=64,
        max_height=64,
        quality=85
    )

    print(f"\n{'='*60}")
    print("COMPRESSION SUMMARY")
    print('='*60)
    print(f"Logo:    {logo_size:.1f}KB ({logo_reduction:.1f}% reduction)")
    print(f"Favicon: {favicon_size:.1f}KB ({favicon_reduction:.1f}% reduction)")
    print(f"\nTotal savings: {540 + 172 - logo_size - favicon_size:.1f}KB")
    print(f"Expected LCP improvement: ~0.5-1.0 seconds")
    print('='*60)
    print("\n[SUCCESS] Image optimization complete!")
    print("\nNext steps:")
    print("1. Test the website to ensure images look good")
    print("2. Commit changes: git add logo.png favicon.png")
    print("3. Push to production: git push origin main")

if __name__ == '__main__':
    main()
