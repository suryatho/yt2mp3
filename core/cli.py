import typer
from typing import Optional

from core.downloader import download_audio

app = typer.Typer()

def identify_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "soundcloud.com" in url:
        return "soundcloud"
    else:
        raise ValueError("Unsupported platform. Only YouTube and SoundCloud are supported.")

@app.command()
def main(url: str = typer.Argument(..., help="YouTube or SoundCloud URL")) -> None:
    try:
        platform = identify_platform(url)
        typer.echo(f"Detected platform: {platform}")
        
        # Generate unique request ID for this CLI session
        request_id = f"cli_{str(hash(url))[:8]}"
        
        download_audio(url, platform=platform, request_id=request_id)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()