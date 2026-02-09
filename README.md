# TikTok Downloader

Tải video, ảnh slideshow và audio từ TikTok không logo, chất lượng cao.

## Tính năng

- **Chế độ Ảnh**: Tải ảnh từ bài slideshow TikTok
- **Chế độ Audio**: Tải video/audio từ TikTok

## Cài đặt

1. Tạo venv và cài dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Chạy server:

```powershell
uvicorn main:app --reload
```

3. Truy cập `http://127.0.0.1:8000`

## Cấu trúc project

```
download-images/
├── core/
│   └── downloader.py      # Logic tải TikTok
├── scripts/
│   ├── update_ytdlp.py    # Script update yt-dlp
│   └── update-yt-dlp.ps1
├── static/
│   ├── index.html         # Giao diện web
│   ├── script.js          # Logic frontend
│   └── style.css          # Styles
├── main.py                # FastAPI server
├── README.md
└── requirements.txt
```

## Cấu hình (tuỳ chọn)

### Proxy

```powershell
$env:PROXY_LIST = "http://user:pass@1.2.3.4:8000, http://user:pass@5.6.7.8:8000"
```

### Debug mode

```powershell
$env:DEBUG_TIKTOK = "1"
```

## Auto-Update yt-dlp

Chạy script bằng Task Scheduler (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update-yt-dlp.ps1
```
