from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import requests
import zipfile
import io
import os
import tempfile
import yt_dlp
from core.downloader import extract_tiktok_info, get_random_user_agent

app = FastAPI(
    title="TikTok Downloader",
    description="API tải video/ảnh TikTok",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class URLRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    urls: list[str]
    filename: str = "tiktok_images.zip"

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/api/extract")
async def extract_info(request: URLRequest):
    data = extract_tiktok_info(request.url)
    if not data:
        raise HTTPException(status_code=400, detail="Không thể lấy thông tin từ link này. Vui lòng kiểm tra lại hoặc thử lại sau.")
    return data

@app.get("/api/download-image")
async def download_image(url: str, filename: str = "image.jpg"):
    """Proxy download for TikTok images"""
    from urllib.parse import quote
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.tiktok.com/"
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Không thể tải ảnh")
        
        # Determine content type
        content_type = response.headers.get("Content-Type", "image/jpeg")
        
        # Encode filename for UTF-8 support
        safe_filename = quote(filename)
        
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

@app.post("/api/download-zip")
async def download_zip(request: DownloadRequest):
    if not request.urls:
        raise HTTPException(status_code=400, detail="Danh sách URL trống")

    # Tạo zip file trong bộ nhớ (RAM)
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for idx, url in enumerate(request.urls):
            try:
                # Tải nội dung ảnh/video
                response = requests.get(url, stream=True, timeout=10)
                if response.status_code == 200:
                    # Xác định tên file
                    filename = f"image_{idx+1}.jpg"
                    if "mp4" in url:
                        filename = f"video_{idx+1}.mp4"
                    elif "mp3" in url:
                        filename = f"audio_{idx+1}.mp3"
                    
                    zip_file.writestr(filename, response.content)
            except Exception as e:
                print(f"Lỗi tải {url}: {e}")
                continue
    
    zip_buffer.seek(0)
    
    # Use custom filename from request
    from urllib.parse import quote
    safe_filename = quote(request.filename)
    
    # Trả về file zip
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )

@app.post("/api/convert-mp3")
async def convert_to_mp3(request: URLRequest):
    """Download TikTok audio/video"""
    import re
    import shutil
    
    clean_url = request.url.split("?", 1)[0].strip()
    clean_url = re.sub(r"/photo/(\d+)", r"/video/\1", clean_url)
    
    # Check if FFmpeg is available
    ffmpeg_available = shutil.which("ffmpeg") is not None
    
    # Create temp directory for download
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "audio.%(ext)s")
    
    # Configure options based on FFmpeg availability
    if ffmpeg_available:
        # With FFmpeg: extract audio as MP3
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "user_agent": get_random_user_agent(),
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
    else:
        # Without FFmpeg: download any available format
        ydl_opts = {
            "outtmpl": output_template,
            "user_agent": get_random_user_agent(),
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
        }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            
            if not info:
                raise HTTPException(status_code=400, detail="Không thể tải video này")
            
            # Find the downloaded file
            downloaded_file = None
            for ext in ["mp3", "m4a", "aac", "ogg", "webm", "mp4"]:
                path = os.path.join(temp_dir, f"audio.{ext}")
                if os.path.exists(path):
                    downloaded_file = path
                    break
            
            if not downloaded_file:
                # Try to find any file in the temp dir
                for f in os.listdir(temp_dir):
                    downloaded_file = os.path.join(temp_dir, f)
                    break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise HTTPException(status_code=500, detail="Không tìm thấy file. Vui lòng thử lại.")
            
            # Read the file and return
            with open(downloaded_file, "rb") as f:
                file_data = f.read()
            
            # Determine content type based on extension
            ext = os.path.splitext(downloaded_file)[1].lower()
            content_types = {
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".aac": "audio/aac",
                ".ogg": "audio/ogg",
                ".webm": "audio/webm",
                ".mp4": "video/mp4",
            }
            content_type = content_types.get(ext, "application/octet-stream")
            
            # Clean up temp files
            for f in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
            
            # Get title for filename
            title = info.get("title", "tiktok_audio")[:50]
            # Clean filename - remove special chars and emoji
            title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title).strip()
            # Remove emoji and non-ASCII characters for filename
            title = title.encode('ascii', 'ignore').decode('ascii').strip()
            if not title:
                title = "tiktok_audio"
            
            # Use urllib to encode filename for Content-Disposition
            from urllib.parse import quote
            safe_filename = quote(f"{title}{ext}")
            
            return StreamingResponse(
                io.BytesIO(file_data),
                media_type=content_type,
                headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Lỗi: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
