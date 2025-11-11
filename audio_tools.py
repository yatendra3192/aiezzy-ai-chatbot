"""
Audio Tools Module for AIezzy
Audio conversion, compression, trimming, and merging utilities

Functions:
- mp4_to_mp3: Extract audio from video files
- audio_converter: Convert between audio formats (MP3, WAV, M4A, OGG, FLAC)
- compress_audio: Reduce audio file size while maintaining quality
- trim_audio: Cut/trim audio files by time range
- merge_audio: Combine multiple audio files into one

Dependencies:
- pydub: Audio processing library
- ffmpeg: Audio/video codec (system dependency)

Created: October 2025
"""

import os
from pydub import AudioSegment
from pydub.utils import mediainfo


def mp4_to_mp3(input_path: str,
               output_name: str = None,
               bitrate: str = '192k',
               quality: str = 'high') -> str:
    """
    Extract audio from MP4 video and save as MP3.

    Args:
        input_path: Path to input MP4 file
        output_name: Name for output file (without extension). If None, auto-generate
        bitrate: MP3 bitrate ('128k', '192k', '256k', '320k')
        quality: Quality preset ('low'=128k, 'medium'=192k, 'high'=256k, 'max'=320k)

    Returns:
        Path to generated MP3 file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Map quality to bitrate
    quality_map = {
        'low': '128k',
        'medium': '192k',
        'high': '256k',
        'max': '320k'
    }

    if quality.lower() in quality_map:
        bitrate = quality_map[quality.lower()]

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_audio"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp3"

    # Load video and extract audio
    print(f"INFO: Extracting audio from {input_path}...")
    audio = AudioSegment.from_file(input_path, format="mp4")

    # Export as MP3
    print(f"INFO: Exporting to MP3 with bitrate {bitrate}...")
    audio.export(output_path, format="mp3", bitrate=bitrate)

    print(f"INFO: MP3 created successfully: {output_path}")
    return output_path


def audio_converter(input_path: str,
                   output_format: str,
                   output_name: str = None,
                   bitrate: str = None,
                   sample_rate: int = None) -> str:
    """
    Convert audio files between formats.

    Args:
        input_path: Path to input audio file
        output_format: Desired output format ('mp3', 'wav', 'm4a', 'ogg', 'flac')
        output_name: Name for output file (without extension). If None, auto-generate
        bitrate: Audio bitrate (e.g., '128k', '192k', '256k', '320k')
                 Only for lossy formats (mp3, ogg, m4a)
        sample_rate: Sample rate in Hz (e.g., 44100, 48000)

    Returns:
        Path to converted audio file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Validate output format
    supported_formats = ['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac']
    output_format = output_format.lower().replace('.', '')

    if output_format not in supported_formats:
        raise ValueError(f"Unsupported format: {output_format}. Supported: {supported_formats}")

    # Detect input format
    input_ext = os.path.splitext(input_path)[1].lower().replace('.', '')
    if not input_ext:
        input_ext = output_format  # Fallback

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_converted"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.{output_format}"

    # Load audio
    print(f"INFO: Loading audio from {input_path}...")
    audio = AudioSegment.from_file(input_path, format=input_ext)

    # Apply sample rate if specified
    if sample_rate:
        audio = audio.set_frame_rate(sample_rate)

    # Export with format-specific settings
    export_params = {'format': output_format}

    if bitrate and output_format in ['mp3', 'ogg', 'm4a', 'aac']:
        export_params['bitrate'] = bitrate

    print(f"INFO: Converting to {output_format.upper()}...")
    audio.export(output_path, **export_params)

    print(f"INFO: Audio converted successfully: {output_path}")
    return output_path


def compress_audio(input_path: str,
                  output_name: str = None,
                  compression_level: str = 'medium',
                  target_bitrate: str = None) -> str:
    """
    Compress audio file to reduce file size.

    Args:
        input_path: Path to input audio file
        output_name: Name for output file (without extension). If None, auto-generate
        compression_level: Compression level ('low', 'medium', 'high')
            - low: 192k bitrate (minimal quality loss)
            - medium: 128k bitrate (balanced)
            - high: 96k bitrate (smaller file, noticeable quality loss)
        target_bitrate: Specific bitrate (e.g., '128k', '96k')

    Returns:
        Path to compressed audio file
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Map compression level to bitrate
    compression_map = {
        'low': '192k',
        'medium': '128k',
        'high': '96k'
    }

    if target_bitrate:
        bitrate = target_bitrate
    else:
        bitrate = compression_map.get(compression_level.lower(), '128k')

    # Detect input format
    input_ext = os.path.splitext(input_path)[1].lower().replace('.', '')
    if not input_ext:
        input_ext = 'mp3'

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_compressed"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp3"

    # Load and compress audio
    print(f"INFO: Loading audio from {input_path}...")
    audio = AudioSegment.from_file(input_path, format=input_ext)

    print(f"INFO: Compressing audio to {bitrate}...")
    audio.export(output_path, format="mp3", bitrate=bitrate)

    # Get file sizes
    original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
    compressed_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    reduction_percent = ((original_size - compressed_size) / original_size) * 100

    print(f"INFO: Compression complete!")
    print(f"      Original: {original_size:.2f} MB")
    print(f"      Compressed: {compressed_size:.2f} MB")
    print(f"      Reduction: {reduction_percent:.1f}%")

    return output_path


def trim_audio(input_path: str,
              start_time: float,
              end_time: float = None,
              duration: float = None,
              output_name: str = None) -> str:
    """
    Trim/cut audio file by time range.

    Args:
        input_path: Path to input audio file
        start_time: Start time in seconds
        end_time: End time in seconds (optional if duration specified)
        duration: Duration in seconds from start_time (optional if end_time specified)
        output_name: Name for output file (without extension). If None, auto-generate

    Returns:
        Path to trimmed audio file

    Example:
        # Trim from 10s to 30s
        trim_audio("song.mp3", start_time=10, end_time=30)

        # Trim 20 seconds starting from 10s
        trim_audio("song.mp3", start_time=10, duration=20)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if end_time is None and duration is None:
        raise ValueError("Either end_time or duration must be specified")

    # Calculate end time if duration provided
    if duration is not None:
        end_time = start_time + duration

    # Convert to milliseconds
    start_ms = int(start_time * 1000)
    end_ms = int(end_time * 1000)

    # Detect input format
    input_ext = os.path.splitext(input_path)[1].lower().replace('.', '')
    if not input_ext:
        input_ext = 'mp3'

    # Generate output path
    if not output_name:
        basename = os.path.splitext(os.path.basename(input_path))[0]
        output_name = f"{basename}_trimmed"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.{input_ext}"

    # Load audio
    print(f"INFO: Loading audio from {input_path}...")
    audio = AudioSegment.from_file(input_path, format=input_ext)

    # Trim audio
    print(f"INFO: Trimming audio from {start_time}s to {end_time}s...")
    trimmed_audio = audio[start_ms:end_ms]

    # Export trimmed audio
    export_format = input_ext if input_ext != '' else 'mp3'
    trimmed_audio.export(output_path, format=export_format)

    print(f"INFO: Audio trimmed successfully: {output_path}")
    return output_path


def merge_audio(input_paths: list,
               output_name: str = None,
               crossfade_duration: float = 0) -> str:
    """
    Merge/combine multiple audio files into one.

    Args:
        input_paths: List of paths to audio files to merge (in order)
        output_name: Name for output file (without extension). If None, auto-generate
        crossfade_duration: Crossfade duration in seconds between tracks (default 0)

    Returns:
        Path to merged audio file

    Example:
        # Simple merge
        merge_audio(["intro.mp3", "main.mp3", "outro.mp3"])

        # Merge with 2-second crossfade
        merge_audio(["song1.mp3", "song2.mp3"], crossfade_duration=2)
    """
    if not input_paths or len(input_paths) < 2:
        raise ValueError("At least 2 audio files are required for merging")

    # Validate all files exist
    for path in input_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Input file not found: {path}")

    # Load first audio file
    print(f"INFO: Loading {len(input_paths)} audio files...")
    combined = AudioSegment.from_file(input_paths[0])

    # Merge remaining files
    crossfade_ms = int(crossfade_duration * 1000)

    for i, path in enumerate(input_paths[1:], 1):
        audio = AudioSegment.from_file(path)

        if crossfade_ms > 0:
            # Append with crossfade
            combined = combined.append(audio, crossfade=crossfade_ms)
        else:
            # Simple append
            combined = combined + audio

        print(f"INFO: Merged {i+1}/{len(input_paths)} files...")

    # Generate output path
    if not output_name:
        output_name = f"merged_audio_{int(__import__('time').time())}"

    os.makedirs('assets', exist_ok=True)
    output_path = f"assets/{output_name}.mp3"

    # Export merged audio
    print(f"INFO: Exporting merged audio...")
    combined.export(output_path, format="mp3", bitrate="192k")

    print(f"INFO: Audio files merged successfully: {output_path}")
    return output_path


# Test functions
if __name__ == "__main__":
    print("Audio Tools Module")
    print("==================\n")
    print("This module requires ffmpeg to be installed on your system.")
    print("Functions available:")
    print("1. mp4_to_mp3() - Extract audio from video")
    print("2. audio_converter() - Convert between audio formats")
    print("3. compress_audio() - Reduce audio file size")
    print("4. trim_audio() - Cut/trim audio files")
    print("5. merge_audio() - Combine multiple audio files\n")
    print("To test these functions, provide sample audio/video files and run specific tests.")
