import subprocess
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, Optional, Any, Union

# Find yt-dlp and ffmpeg in PATH
YTDLP_PATH: str = shutil.which("yt-dlp") or "yt-dlp"
FFMPEG_PATH: str = shutil.which("ffmpeg") or "ffmpeg"

DOWNLOAD_DIR: Path = Path.home() / "Documents" / "Spotify"

def get_metadata_from_url(url: str) -> Dict[str, Optional[str]]:
    # Use yt-dlp to get all metadata in one call
    cmd: list[str] = [YTDLP_PATH, '--quiet', '--skip-download', '--dump-json', url]
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise e
    data: Dict[str, Any] = json.loads(result.stdout)
    return {
        "title": data.get("title"),
        "uploader": data.get("uploader"),
        "release_date": data.get("release_date")  # Format: YYYYMMDD or None
    }

def set_file_mtime(filepath: Union[str, Path], release_date: Optional[str]) -> None:
    if not release_date or len(release_date) != 8:
        return
    dt: datetime = datetime.strptime(release_date, "%Y%m%d")
    mod_time: float = dt.timestamp()
    os.utime(filepath, (mod_time, mod_time))

def sanitize_filename(name: str) -> str:
    # Replace / and \ and other forbidden characters with _
    return re.sub(r'[\\/:"*?<>|]+', '_', name)

def download_audio(url: str, title: Optional[str] = None) -> None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    temp_path: Path = DOWNLOAD_DIR / "temp_audio.%(ext)s"
    temp_mp3: Path = DOWNLOAD_DIR / "temp_audio.mp3"
    temp_thumbnail: Path = DOWNLOAD_DIR / "thumbnail.jpg"

    # Get metadata in one call
    metadata: Dict[str, Optional[str]] = get_metadata_from_url(url)
    final_title: Optional[str] = title if title else metadata["title"]
    artist: Optional[str] = metadata["uploader"]
    release_date: Optional[str] = metadata["release_date"]
    final_path: Path = DOWNLOAD_DIR / f"{sanitize_filename(final_title or 'untitled')}.mp3"

    # Download audio and thumbnail
    cmd: list[str] = [
        YTDLP_PATH,
        '--extract-audio',
        '--audio-format', 'mp3',
        '--output', str(temp_path),
        '--write-thumbnail',
        url
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL
        )
    except Exception as e:
        raise e

    # Find the downloaded thumbnail (yt-dlp may save as .webp or .jpg)
    thumb_file: Optional[Path] = None
    for ext in ['jpg', 'webp', 'png']:
        candidate: Path = DOWNLOAD_DIR / f"temp_audio.{ext}"
        if candidate.exists():
            thumb_file = candidate
            break

    # Convert thumbnail to jpg if needed
    if thumb_file and thumb_file.suffix != ".jpg":
        try:
            subprocess.run(
                [
                    FFMPEG_PATH, "-y", "-i", str(thumb_file), str(temp_thumbnail)
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
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
    
    cover_args: list[str] = []
    if thumb_file and thumb_file.exists():
        cover_args = ["-i", str(thumb_file), "-map", "0:a", "-map", "1", "-c", "copy", "-id3v2_version", "3", "-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)"]

    # Set metadata and embed thumbnail
    ffmpeg_cmd: list[str] = [
        FFMPEG_PATH, "-y", "-i", str(temp_mp3)
    ] + (cover_args if cover_args else []) + metadata_args + [str(final_path)]
    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        raise e

    # Set file modification time to release date if available
    if final_path.exists() and release_date:
        set_file_mtime(final_path, release_date)

    # Clean up temp files
    if temp_mp3.exists():
        temp_mp3.unlink()
    if thumb_file and thumb_file.exists():
        thumb_file.unlink()

    print(f"✅ Downloaded to: {final_path}")