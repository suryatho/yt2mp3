import subprocess
import json
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, Optional, Any, Union

# Configure logging to write to the same file as server
logging.basicConfig(
    filename="/tmp/spotifytool-server.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    force=True  # Override any existing config
)

# Find yt-dlp, ffmpeg, and scdl in PATH
YTDLP_PATH: str = shutil.which("yt-dlp") or "yt-dlp"
FFMPEG_PATH: str = shutil.which("ffmpeg") or "ffmpeg"
SCDL_PATH: str = shutil.which("scdl") or "scdl"

DOWNLOAD_DIR: Path = Path.home() / "Documents" / "Spotify"

def clean_youtube_url(url: str) -> str:
    """Clean YouTube URL by removing playlist and other problematic parameters"""
    import urllib.parse as urlparse
    
    parsed = urlparse.urlparse(url)
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        query_params = urlparse.parse_qs(parsed.query)
        # Keep only the video ID parameter, remove playlist and other params
        if 'v' in query_params:
            clean_query = f"v={query_params['v'][0]}"
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
        elif 'youtu.be' in parsed.netloc:
            # For youtu.be URLs, just return the base URL without query params
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    return url  # Return original URL if not YouTube or already clean

def get_metadata_from_url(url: str) -> Dict[str, Optional[str]]:
    # Clean the URL first to avoid playlist issues
    clean_url = clean_youtube_url(url)
    if clean_url != url:
        logging.info(f"Cleaned URL from {url} to {clean_url}")
    
    # Use yt-dlp to get all metadata in one call with timeout
    cmd: list[str] = [YTDLP_PATH, '--quiet', '--skip-download', '--dump-json', '--socket-timeout', '30', clean_url]
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=45  # 45 second timeout for metadata fetch
        )
        data: Dict[str, Any] = json.loads(result.stdout)
        return {
            "title": data.get("title"),
            "uploader": data.get("uploader"),
            "release_date": data.get("release_date")  # Format: YYYYMMDD or None
        }
    except subprocess.TimeoutExpired:
        logging.error(f"yt-dlp metadata fetch timed out for {clean_url}")
        raise RuntimeError(f"Metadata fetch timed out. The URL might be invalid or inaccessible.")
    except subprocess.CalledProcessError as e:
        logging.error(f"yt-dlp metadata fetch failed for {clean_url}: return code {e.returncode}")
        if e.stderr:
            logging.error(f"yt-dlp stderr: {e.stderr}")
        if e.stdout:
            logging.error(f"yt-dlp stdout: {e.stdout}")
        raise RuntimeError(f"Failed to get metadata: Video might be private, deleted, or URL is invalid (error code {e.returncode})")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse yt-dlp JSON output for {clean_url}: {e}")
        raise RuntimeError(f"Invalid response from video platform for {clean_url}")
    except Exception as e:
        logging.error(f"Unexpected error getting metadata for {clean_url}: {e}")
        raise RuntimeError(f"Unexpected error getting metadata: {e}")

def set_file_mtime(filepath: Union[str, Path], release_date: Optional[str]) -> None:
    if not release_date or len(release_date) != 8:
        return
    dt: datetime = datetime.strptime(release_date, "%Y%m%d")
    mod_time: float = dt.timestamp()
    os.utime(filepath, (mod_time, mod_time))

def sanitize_filename(name: str) -> str:
    # Replace / and \ and other forbidden characters with _
    return re.sub(r'[\\/:"*?<>|]+', '_', name)

def download_audio(url: str, title: Optional[str] = None, platform: str = "youtube", request_id: Optional[str] = None) -> None:
    import time
    start_time = time.time()
    unique_id = request_id or str(hash(url))[:8]
    
    logging.info(f"[{unique_id}] Starting download_audio function - URL: {url}, Platform: {platform}, Title: {title}")
    
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        logging.info(f"[{unique_id}] Created download directory: {DOWNLOAD_DIR}")
    except Exception as e:
        logging.error(f"[{unique_id}] Failed to create download directory: {e}")
        raise RuntimeError(f"Failed to create download directory: {e}")
    
    if platform == "youtube":
        logging.info(f"[{unique_id}] Processing YouTube download...")
        
        # Get metadata first to validate URL and get info
        logging.info(f"[{unique_id}] Fetching metadata from URL...")
        try:
            metadata: Dict[str, Optional[str]] = get_metadata_from_url(url)
            final_title: Optional[str] = title if title else metadata["title"]
            artist: Optional[str] = metadata["uploader"]
            release_date: Optional[str] = metadata["release_date"]
            logging.info(f"[{unique_id}] Metadata retrieved - Title: {final_title}, Artist: {artist}")
        except Exception as e:
            logging.error(f"[{unique_id}] Failed to get metadata: {e}")
            raise e
        
        # Set up temp file paths after successful metadata fetch
        temp_path: Path = DOWNLOAD_DIR / f"temp_audio_{unique_id}.%(ext)s"
        temp_mp3: Path = DOWNLOAD_DIR / f"temp_audio_{unique_id}.mp3"
        temp_thumbnail: Path = DOWNLOAD_DIR / f"thumbnail_{unique_id}.jpg"
        final_path: Path = DOWNLOAD_DIR / f"{sanitize_filename(final_title or 'untitled')}.mp3"

        # Download audio and thumbnail using the cleaned URL
        clean_url = clean_youtube_url(url)
        cmd: list[str] = [
            YTDLP_PATH,
            '--extract-audio',
            '--audio-format', 'mp3',
            '--output', str(temp_path),
            '--write-thumbnail',
            '--socket-timeout', '30',
            '--retries', '5',
            '--fragment-retries', '5',
            '--sleep-interval', '1',
            '--max-sleep-interval', '10',
            '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-args', 'youtube:player_client=android,web',
            '--no-check-certificates',
            '--ignore-errors',
            clean_url
        ]
        logging.info(f"[{unique_id}] Starting yt-dlp download with command: {' '.join(cmd)}")
        
        # Try the main download first
        success = False
        for attempt in range(2):
            try:
                if attempt == 1:
                    # Second attempt: try with different extractor args
                    logging.info(f"[{unique_id}] First attempt failed, trying alternative extraction method...")
                    cmd = [
                        YTDLP_PATH,
                        '--extract-audio',
                        '--audio-format', 'mp3',
                        '--output', str(temp_path),
                        '--write-thumbnail',
                        '--socket-timeout', '30',
                        '--retries', '10',
                        '--fragment-retries', '10',
                        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        '--extractor-args', 'youtube:player_client=android_music,android,web',
                        '--no-check-certificates',
                        '--ignore-errors',
                        '--force-ipv4',
                        clean_url
                    ]
                    logging.info(f"[{unique_id}] Retry command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout for download
                    cwd=str(DOWNLOAD_DIR)  # Set working directory
                )
                logging.info(f"[{unique_id}] yt-dlp download completed successfully on attempt {attempt + 1}")
                if result.stdout:
                    logging.info(f"[{unique_id}] yt-dlp stdout: {result.stdout[:200]}")
                success = True
                break
                
            except subprocess.TimeoutExpired:
                logging.error(f"[{unique_id}] yt-dlp download timed out on attempt {attempt + 1}")
                if attempt == 1:
                    raise RuntimeError(f"Download timed out after 5 minutes on all attempts. The video might be too large or connection is slow.")
            except subprocess.CalledProcessError as e:
                logging.error(f"[{unique_id}] yt-dlp download failed on attempt {attempt + 1} with return code {e.returncode}")
                logging.error(f"[{unique_id}] yt-dlp stderr: {e.stderr}")
                if e.stdout:
                    logging.error(f"[{unique_id}] yt-dlp stdout: {e.stdout}")
                if attempt == 1:
                    raise RuntimeError(f"Download failed on all attempts: yt-dlp error code {e.returncode}. YouTube may be blocking this video.")
            except Exception as e:
                logging.error(f"[{unique_id}] Unexpected error during yt-dlp download on attempt {attempt + 1}: {e}")
                if attempt == 1:
                    raise RuntimeError(f"Unexpected download error on all attempts: {e}")
        
        if not success:
            raise RuntimeError("Download failed on all attempts")

        logging.info(f"[{unique_id}] yt-dlp download complete, starting post-processing...")

        # Check if the main audio file was created
        if not temp_mp3.exists():
            logging.error(f"[{unique_id}] Audio file not found at {temp_mp3}")
            raise RuntimeError("Audio file was not created by yt-dlp")
        
        logging.info(f"[{unique_id}] Audio file found at {temp_mp3}")

        # Find the downloaded thumbnail (yt-dlp may save as .webp or .jpg)
        thumb_file: Optional[Path] = None
        for ext in ['jpg', 'webp', 'png']:
            candidate: Path = DOWNLOAD_DIR / f"temp_audio_{unique_id}.{ext}"
            if candidate.exists():
                thumb_file = candidate
                logging.info(f"[{unique_id}] Found thumbnail: {candidate}")
                break
        
        if not thumb_file:
            logging.info(f"[{unique_id}] No thumbnail found")

        # Convert thumbnail to jpg if needed
        if thumb_file and thumb_file.suffix != ".jpg":
            logging.info(f"[{unique_id}] Converting thumbnail from {thumb_file.suffix} to .jpg")
            try:
                subprocess.run(
                    [
                        FFMPEG_PATH, "-y", "-i", str(thumb_file), str(temp_thumbnail)
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30  # Add timeout for ffmpeg
                )
                logging.info(f"[{unique_id}] Thumbnail conversion completed")
            except subprocess.TimeoutExpired:
                logging.error(f"[{unique_id}] Thumbnail conversion timed out")
                raise RuntimeError("Thumbnail conversion timed out")
            except Exception as e:
                logging.error(f"[{unique_id}] Thumbnail conversion failed: {e}")
                raise e
            thumb_file.unlink()
            thumb_file = temp_thumbnail

        # Prepare ffmpeg metadata args
        metadata_args: list[str] = ["-metadata", f"title={final_title or 'untitled'}"]
        if artist:
            metadata_args += ["-metadata", f"artist={artist}"]
        if release_date and len(release_date) == 8:
            year: str = release_date[:4]
            metadata_args += ["-metadata", f"date={year}"]

        # First, just copy the audio with basic metadata (no thumbnail)
        logging.info(f"[{unique_id}] Starting basic metadata processing (no thumbnail)...")
        basic_ffmpeg_cmd: list[str] = [
            FFMPEG_PATH, "-y", "-i", str(temp_mp3), "-c", "copy"
        ] + metadata_args + [str(final_path)]
        
        logging.info(f"[{unique_id}] Basic FFmpeg command: {' '.join(basic_ffmpeg_cmd)}")
        
        try:
            subprocess.run(
                basic_ffmpeg_cmd,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,  # 1 minute timeout for basic processing
                cwd=str(DOWNLOAD_DIR)  # Set working directory
            )
            logging.info(f"[{unique_id}] Basic metadata processing completed")
        except subprocess.TimeoutExpired:
            logging.error(f"[{unique_id}] Basic metadata processing timed out")
            raise RuntimeError("Basic metadata processing timed out")
        except Exception as e:
            logging.error(f"[{unique_id}] Basic metadata processing failed: {e}")
            raise e

        # Now try to add thumbnail if available (optional, don't fail if it doesn't work)
        if thumb_file and thumb_file.exists():
            logging.info(f"[{unique_id}] Attempting to embed thumbnail...")
            temp_with_thumb = DOWNLOAD_DIR / f"temp_with_thumb_{unique_id}.mp3"
            
            thumb_ffmpeg_cmd: list[str] = [
                FFMPEG_PATH, "-y", 
                "-i", str(final_path), 
                "-i", str(thumb_file),
                "-map", "0:a", "-map", "1:0", 
                "-c:a", "copy", "-c:v", "mjpeg",
                "-id3v2_version", "3",
                "-metadata:s:v", "title=Album cover", 
                "-metadata:s:v", "comment=Cover (front)",
                str(temp_with_thumb)
            ]
            
            try:
                subprocess.run(
                    thumb_ffmpeg_cmd,
                    check=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,  # 1 minute timeout for thumbnail embedding
                    cwd=str(DOWNLOAD_DIR)  # Set working directory
                )
                logging.info(f"[{unique_id}] Thumbnail embedding completed successfully")
                # Replace the original with the one that has thumbnail
                final_path.unlink()
                temp_with_thumb.rename(final_path)
            except subprocess.TimeoutExpired:
                logging.warning(f"[{unique_id}] Thumbnail embedding timed out, keeping file without thumbnail")
                if temp_with_thumb.exists():
                    temp_with_thumb.unlink()
            except Exception as e:
                logging.warning(f"[{unique_id}] Thumbnail embedding failed: {e}, keeping file without thumbnail")
                if temp_with_thumb.exists():
                    temp_with_thumb.unlink()
        else:
            logging.info(f"[{unique_id}] No thumbnail to embed")

        # Set file modification time to release date if available
        if final_path.exists() and release_date:
            logging.info(f"[{unique_id}] Setting file modification time to {release_date}")
            set_file_mtime(final_path, release_date)

        # Clean up all temp files
        logging.info(f"[{unique_id}] Cleaning up temporary files...")
        temp_files = [temp_mp3, temp_thumbnail]
        if thumb_file and thumb_file != temp_thumbnail:
            temp_files.append(thumb_file)
        
        for temp_file in temp_files:
            if temp_file and temp_file.exists():
                temp_file.unlink()
        
        # Also clean up any remaining temp files for this specific download
        for pattern in [f'temp_audio_{unique_id}.*', f'thumbnail_{unique_id}.*']:
            for leftover in DOWNLOAD_DIR.glob(pattern):
                if leftover.exists():
                    leftover.unlink()

        print(f"✅ Downloaded to: {final_path}")
        logging.info(f"[{unique_id}] YouTube download completed successfully: {final_path}")
        logging.info(f"[{unique_id}] Final file size: {final_path.stat().st_size if final_path.exists() else 'File not found'} bytes")
    elif platform == "soundcloud":
        # SoundCloud download logic using scdl
        # scdl handles metadata quite well on its own, but we can enhance it
        
        # First try to get metadata using yt-dlp for consistency
        try:
            metadata: Dict[str, Optional[str]] = get_metadata_from_url(url)
            final_title: Optional[str] = title if title else metadata["title"]
        except Exception:
            # Fallback if yt-dlp can't handle the SoundCloud URL
            final_title = title
        
        # Use scdl to download with proper options
        cmd: list[str] = [
            SCDL_PATH,
            "-l", url,
            "--path", str(DOWNLOAD_DIR),  # Use --path for output directory
            "--onlymp3",
            "--original-art",  # Download original cover art
            "--extract-artist"  # Set artist tag from title instead of username
        ]
        
        # Add custom name format if we have a title
        if final_title:
            sanitized_title = sanitize_filename(final_title)
            cmd.extend(["--name-format", f"{sanitized_title}.%(ext)s"])
        
        try:
            subprocess.run(
                cmd, 
                check=True,
                # stdout=subprocess.DEVNULL,
                # stderr=subprocess.DEVNULL
            )
            print(f"✅ Downloaded SoundCloud track to: {DOWNLOAD_DIR}")
            logging.info(f"SoundCloud download completed to: {DOWNLOAD_DIR}")
        except subprocess.CalledProcessError as e:
            logging.error(f"SoundCloud download failed: {e}")
            raise RuntimeError(f"SoundCloud download failed: {e}")
    else:
        raise ValueError("Unsupported platform. Only YouTube and SoundCloud are supported.")