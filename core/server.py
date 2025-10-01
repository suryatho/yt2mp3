from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from core.downloader import download_audio

# Set up logging
logging.basicConfig(
    filename="/tmp/yt2mp3-server.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

app = FastAPI()

class DownloadRequest(BaseModel):
    url: str
    title: Optional[str] = None

@app.post("/download")
async def download(request: DownloadRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    logging.info(f"Download requested: {request.url}, title: {request.title}")
    try:
        background_tasks.add_task(download_audio, request.url, request.title)
        return {"status": "success", "message": "Download started"}
    except Exception as e:
        logging.error(f"Download failed: {str(e)}", exc_info=True)
        return {"status": "error", "reason": str(e)}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "online"}

def start_server() -> None:
    """Entry point for pipx script"""
    uvicorn.run(app, host="127.0.0.1", port=5000)

if __name__ == "__main__":
    start_server()