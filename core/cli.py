import subprocess
import typer
from typing import List, Dict, Optional

from core.downloader import download_audio

app = typer.Typer()

def search_youtube(query: str) -> List[Dict[str, str]]:
    cmd: List[str] = [
        'yt-dlp',
        '--quiet',
        '--flat-playlist',
        '--skip-download',
        '--default-search', 'ytsearch10',
        '--print', '%(title)s\t%(uploader)s\t%(url)s',
        query
    ]
    result: subprocess.CompletedProcess = subprocess.run(cmd, capture_output=True, text=True, check=True)
    entries: List[Dict[str, str]] = []
    for line in result.stdout.splitlines():
        if line.strip():
            title: str
            uploader: str
            url: str
            title, uploader, url = line.split('\t', 2)
            entries.append({'title': title, 'uploader': uploader, 'url': url})
    return entries

@app.command()
def main(
    u: Optional[str] = typer.Option(None, "--url", "-u", help="YouTube URL"),
    q: Optional[str] = typer.Option(None, "--query", "-q", help="Search query")
) -> None:
    url: Optional[str] = None
    if u:
        url = u
    elif q:
        entries: List[Dict[str, str]] = search_youtube(q)
        if not entries:
            typer.echo("No results found.")
            raise typer.Exit()
        typer.echo("\nSearch Results:")
        for idx, entry in enumerate(entries):
            typer.echo(f"{idx}. {entry['title']} [{entry['uploader']}]")
        choice: str = typer.prompt(f"Select a video (0-{len(entries)-1})")
        try:
            idx: int = int(choice)
            if 0 <= idx < len(entries):
                url = entries[idx]['url']
            else:
                typer.echo("Invalid selection.")
                raise typer.Exit()
        except ValueError:
            typer.echo("Invalid input.")
            raise typer.Exit()
    else:
        typer.echo("Please provide either --url/-u or --query/-q.")
        raise typer.Exit()

    # Ask for title (optional)
    title: Optional[str] = typer.prompt("Enter a title for the download (leave blank to auto-detect)", default="").strip()
    if not title:
        title = None
    typer.echo(f"Downloading: {title if title else 'Auto-detecting title...'}")
    try:
        download_audio(url, title)  # title can be None
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {e.cmd}\nReturn code: {e.returncode}\nOutput: {e.output}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download audio: {e}") from e

if __name__ == "__main__":
    app()