from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict, Any
import logging
import asyncio
import functools

from core.downloader import download_audio

# Set up logging
logging.basicConfig(
    filename="/tmp/spotifytool-server.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

app = FastAPI()

# Add CORS middleware to handle browser extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class DownloadRequest(BaseModel):
    url: str
    title: Optional[str] = None

def identify_platform(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "soundcloud.com" in url:
        return "soundcloud"
    else:
        raise ValueError("Unsupported platform. Only YouTube and SoundCloud are supported.")

@app.post("/download")
async def download(request: DownloadRequest) -> Dict[str, str]:
    import time
    start_time = time.time()
    request_id = f"{hash(request.url)}_{hash(request.title or 'notitle')}"
    logging.info(f"Download requested [{request_id}]: {request.url}, title: {request.title}")
    
    try:
        # Identify platform from URL
        platform = identify_platform(request.url)
        logging.info(f"Detected platform [{request_id}]: {platform}")
        
        # Log before starting download
        logging.info(f"Starting download process [{request_id}]...")
        
        # Run download_audio in thread pool to avoid blocking other requests
        # Each request gets its own thread, so multiple downloads can run concurrently
        loop = asyncio.get_event_loop()
        
        # Explicitly handle the download result
        try:
            await loop.run_in_executor(
                None, 
                functools.partial(download_audio, request.url, title=request.title, platform=platform, request_id=request_id)
            )
        except Exception as download_error:
            # Re-raise download errors to be caught by outer try-catch
            logging.error(f"Download function failed [{request_id}]: {download_error}")
            raise download_error
        
        elapsed_time = time.time() - start_time
        logging.info(f"Download completed successfully [{request_id}] in {elapsed_time:.2f} seconds: {request.url}")
        return {"status": "success", "message": f"Download completed in {elapsed_time:.1f}s"}
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        logging.error(f"Download failed [{request_id}] after {elapsed_time:.2f} seconds: {error_msg}", exc_info=True)
        return {"status": "error", "reason": error_msg}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "online"}

@app.get("/test-error")
async def test_error() -> Dict[str, str]:
    """Test endpoint to verify error handling works"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: (_ for _ in ()).throw(RuntimeError("Test error")))
        return {"status": "success", "message": "This should not appear"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def start_server() -> None:
    """Entry point for pipx script"""
    uvicorn.run(app, host="127.0.0.1", port=5000)

if __name__ == "__main__":
    start_server()