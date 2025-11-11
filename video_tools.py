"""
Video Tools Module for AIezzy
Video conversion, compression, trimming, and speed adjustment utilities

Functions:
- video_to_gif: Convert video clips to animated GIF
- compress_video: Reduce video file size while maintaining quality
- trim_video: Cut/trim video segments by time range
- change_video_speed: Speed up or slow down video playback

Dependencies:
- moviepy: Video editing library
- ffmpeg: Video codec (system dependency)
- imageio: GIF creation

Created: October 2025
"""

import os
from moviepy.editor import VideoFileClip
from moviepy.video.fx import speedx


def video_to_gif(input_path: str,
                 output_name: str = None,
                 start_time: float = 0,
                 duration: float = None,
                 fps: int = 10,
                 width: int = None,
                 height: int = None,
                 optimize: bool = True) -> str:
    """
    Convert video to animated GIF.

    Args:
        input_path: Path to input video file
        output_name: Name for output file (without extension). If None, auto-generate
        start_time: Start time in seconds (default 0)
        duration: Duration in seconds from start_time (None = full video from start)
        fps: Frames per second for GIF (lower = smaller file, default 10)
        width: Output width in pixels (maintains aspect ratio if height not specified)
        height: Output height in pixels
        optimize: Optimize GIF file size (default True)

    Returns:
        Path to generated GIF file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_animated"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.gif"

    print(f"INFO: Loading video from {input_path}...")

    # Load video
    clip = VideoFileClip(input_path)

    # Calculate end time
    if duration:
        end_time = start_time + duration
    else:
        end_time = clip.duration

    # Trim video to specified range
    if start_time > 0 or duration:
        clip = clip.subclip(start_time, end_time)
        print(f"INFO: Trimmed video from {start_time}s to {end_time}s")

    # Resize if dimensions specified
    if width or height:
        if width and not height:
            # Resize by width, maintain aspect ratio
            clip = clip.resize(width=width)
        elif height and not width:
            # Resize by height, maintain aspect ratio
            clip = clip.resize(height=height)
        else:
            # Resize to specific dimensions
            clip = clip.resize((width, height))
        print(f"INFO: Resized to {clip.w}x{clip.h}")

    # Convert to GIF
    print(f"INFO: Converting to GIF at {fps} FPS...")
    clip.write_gif(
        output_path,
        fps=fps,
        program='ffmpeg',
        opt='nq' if optimize else None
    )

    clip.close()

    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    print(f"INFO: GIF created successfully: {output_path} ({file_size:.2f} MB)")

    return output_path


def compress_video(input_path: str,
                  output_name: str = None,
                  quality: str = 'medium',
                  target_resolution: str = None,
                  bitrate: str = None) -> str:
    """
    Compress video to reduce file size.

    Args:
        input_path: Path to input video file
        output_name: Name for output file (without extension). If None, auto-generate
        quality: Compression quality ('low', 'medium', 'high')
            - low: Aggressive compression (smaller file, lower quality)
            - medium: Balanced (default)
            - high: Minimal compression (larger file, better quality)
        target_resolution: Target resolution ('1080p', '720p', '480p', '360p')
        bitrate: Specific bitrate (e.g., '1000k', '2000k')

    Returns:
        Path to compressed video file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Map quality to bitrate
    quality_map = {
        'low': '500k',
        'medium': '1000k',
        'high': '2000k'
    }

    if not bitrate:
        bitrate = quality_map.get(quality.lower(), '1000k')

    # Map resolution strings to dimensions
    resolution_map = {
        '1080p': (1920, 1080),
        '720p': (1280, 720),
        '480p': (854, 480),
        '360p': (640, 360)
    }

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_compressed"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp4"

    print(f"INFO: Loading video from {input_path}...")

    # Load video
    clip = VideoFileClip(input_path)

    # Resize if target resolution specified
    if target_resolution and target_resolution.lower() in resolution_map:
        target_width, target_height = resolution_map[target_resolution.lower()]

        # Only resize if original is larger
        if clip.w > target_width or clip.h > target_height:
            clip = clip.resize(height=target_height)
            print(f"INFO: Resized to {clip.w}x{clip.h}")

    # Compress video
    print(f"INFO: Compressing video with bitrate {bitrate}...")
    clip.write_videofile(
        output_path,
        codec='libx264',
        bitrate=bitrate,
        audio_codec='aac',
        audio_bitrate='128k',
        preset='medium',
        logger=None  # Suppress progress bar
    )

    clip.close()

    # Get file sizes
    original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
    compressed_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    reduction_percent = ((original_size - compressed_size) / original_size) * 100

    print(f"INFO: Compression complete!")
    print(f"      Original: {original_size:.2f} MB")
    print(f"      Compressed: {compressed_size:.2f} MB")
    print(f"      Reduction: {reduction_percent:.1f}%")

    return output_path


def trim_video(input_path: str,
              start_time: float,
              end_time: float = None,
              duration: float = None,
              output_name: str = None) -> str:
    """
    Trim/cut video by time range.

    Args:
        input_path: Path to input video file
        start_time: Start time in seconds
        end_time: End time in seconds (optional if duration specified)
        duration: Duration in seconds from start_time (optional if end_time specified)
        output_name: Name for output file (without extension). If None, auto-generate

    Returns:
        Path to trimmed video file

    Example:
        # Trim from 10s to 30s
        trim_video("video.mp4", start_time=10, end_time=30)

        # Trim 20 seconds starting from 10s
        trim_video("video.mp4", start_time=10, duration=20)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if end_time is None and duration is None:
        raise ValueError("Either end_time or duration must be specified")

    # Calculate end time if duration provided
    if duration is not None:
        end_time = start_time + duration

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_trimmed"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp4"

    print(f"INFO: Loading video from {input_path}...")

    # Load and trim video
    clip = VideoFileClip(input_path)
    print(f"INFO: Trimming video from {start_time}s to {end_time}s...")
    trimmed_clip = clip.subclip(start_time, end_time)

    # Export trimmed video
    trimmed_clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        logger=None
    )

    clip.close()
    trimmed_clip.close()

    print(f"INFO: Video trimmed successfully: {output_path}")
    return output_path


def change_video_speed(input_path: str,
                      speed_factor: float,
                      output_name: str = None) -> str:
    """
    Change video playback speed (speed up or slow down).

    Args:
        input_path: Path to input video file
        speed_factor: Speed multiplier
            - 0.5 = half speed (slow motion)
            - 1.0 = normal speed
            - 2.0 = double speed (fast forward)
            - 0.25 = quarter speed (very slow)
            - 4.0 = quadruple speed (very fast)
        output_name: Name for output file (without extension). If None, auto-generate

    Returns:
        Path to speed-adjusted video file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if speed_factor <= 0:
        raise ValueError("Speed factor must be greater than 0")

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        if speed_factor > 1:
            output_name = f"{basename}_fast{speed_factor}x"
        else:
            output_name = f"{basename}_slow{speed_factor}x"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp4"

    print(f"INFO: Loading video from {input_path}...")

    # Load video
    clip = VideoFileClip(input_path)

    # Change speed
    print(f"INFO: Changing video speed to {speed_factor}x...")
    final_clip = speedx.speedx(clip, factor=speed_factor)

    # Export video
    final_clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        logger=None
    )

    clip.close()
    final_clip.close()

    original_duration = clip.duration
    new_duration = original_duration / speed_factor

    print(f"INFO: Video speed changed successfully: {output_path}")
    print(f"      Original duration: {original_duration:.1f}s")
    print(f"      New duration: {new_duration:.1f}s")

    return output_path


# Test functions
if __name__ == "__main__":
    print("Video Tools Module")
    print("==================\n")
    print("This module requires ffmpeg to be installed on your system.")
    print("Functions available:")
    print("1. video_to_gif() - Convert video clips to animated GIF")
    print("2. compress_video() - Reduce video file size")
    print("3. trim_video() - Cut/trim video segments")
    print("4. change_video_speed() - Speed up or slow down video\n")
    print("To test these functions, provide sample video files and run specific tests.")
