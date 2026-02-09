import logging
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
import yt_dlp
from fake_useragent import UserAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    ua = UserAgent()
except Exception:
    ua = None


def get_random_user_agent() -> str:
    try:
        if ua:
            return ua.random
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    except Exception:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )


def get_proxy() -> Optional[str]:
    raw = os.getenv("PROXY_LIST", "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in re.split(r"[\n,]", raw) if p.strip()]
    if not parts:
        return None
    return parts[0]


def _dedupe_key(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path


def _add_url(urls: List[str], url: Optional[str], seen: Optional[set] = None) -> None:
    if not url:
        return
    key = _dedupe_key(url)
    if seen is not None:
        if key in seen:
            return
        seen.add(key)
    if url not in urls:
        urls.append(url)


def _extract_images(info: Dict) -> List[str]:
    urls: List[str] = []
    seen: set = set()

    images = info.get("images") or []
    if isinstance(images, list):
        for img in images:
            if isinstance(img, dict):
                _add_url(urls, img.get("url"), seen)
                url_list = img.get("url_list") or []
                if isinstance(url_list, list):
                    for u in url_list:
                        _add_url(urls, u, seen)
            elif isinstance(img, str):
                _add_url(urls, img, seen)

    entries = info.get("entries") or []
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                _add_url(urls, entry.get("url"), seen)
                entry_images = entry.get("images") or []
                if isinstance(entry_images, list):
                    for img in entry_images:
                        if isinstance(img, dict):
                            _add_url(urls, img.get("url"), seen)
                            url_list = img.get("url_list") or []
                            if isinstance(url_list, list):
                                for u in url_list:
                                    _add_url(urls, u, seen)
                        elif isinstance(img, str):
                            _add_url(urls, img, seen)
                entry_thumbs = entry.get("thumbnails") or []
                if isinstance(entry_thumbs, list):
                    for t in entry_thumbs:
                        if isinstance(t, dict):
                            _add_url(urls, t.get("url"), seen)
                entry_formats = entry.get("formats") or []
                if isinstance(entry_formats, list):
                    for fmt in entry_formats:
                        if not isinstance(fmt, dict):
                            continue
                        url = fmt.get("url")
                        ext = (fmt.get("ext") or "").lower()
                        fmt_id = (fmt.get("format_id") or "").lower()
                        if ext in {"jpg", "jpeg", "png", "webp"} or "image" in fmt_id or "photo" in fmt_id:
                            _add_url(urls, url, seen)

    formats = info.get("formats") or []
    if isinstance(formats, list):
        for fmt in formats:
            if not isinstance(fmt, dict):
                continue
            url = fmt.get("url")
            ext = (fmt.get("ext") or "").lower()
            fmt_id = (fmt.get("format_id") or "").lower()
            if ext in {"jpg", "jpeg", "png", "webp"} or "image" in fmt_id or "photo" in fmt_id:
                _add_url(urls, url, seen)

    if not urls:
        thumbs = info.get("thumbnails") or []
        if isinstance(thumbs, list):
            for t in thumbs:
                if isinstance(t, dict):
                    _add_url(urls, t.get("url"), seen)

    return urls


def _extract_audio(info: Dict) -> Optional[str]:
    # Try music field first
    music = info.get("music")
    if isinstance(music, dict):
        url = music.get("play_url") or music.get("url")
        if url:
            return url
    
    # Try audio field
    audio = info.get("audio")
    if isinstance(audio, dict):
        url = audio.get("url")
        if url:
            return url
    
    # Try formats for audio
    formats = info.get("formats") or []
    if isinstance(formats, list):
        for fmt in formats:
            if not isinstance(fmt, dict):
                continue
            fmt_id = (fmt.get("format_id") or "").lower()
            ext = (fmt.get("ext") or "").lower()
            vcodec = (fmt.get("vcodec") or "")
            # Check if it's audio only format
            if fmt_id == "audio" or ext in {"mp3", "m4a", "aac", "ogg"} or vcodec == "none":
                url = fmt.get("url")
                if url:
                    return url
    
    # Fallback: check if main url is audio (for slideshow posts)
    main_ext = (info.get("ext") or "").lower()
    if main_ext in {"mp3", "m4a", "aac", "ogg"}:
        return info.get("url")
    
    # Final fallback: get url if it looks like audio
    main_url = info.get("url") or ""
    if "audio" in main_url or "mp3" in main_url:
        return main_url
    
    return None
    
    return None


def _extract_images_from_embed(item_id: str) -> List[str]:
    urls: List[str] = []
    seen: set = set()
    if not item_id:
        return urls

    embed_url = f"https://www.tiktok.com/embed/v2/{item_id}"
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(embed_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return urls
        text = resp.text
    except Exception as e:
        logger.error("Embed fetch error: %s", e)
        return urls

    key = "\"imagePostInfo\":"
    idx = text.find(key)
    if idx == -1:
        return urls

    start = text.find("{", idx)
    if start == -1:
        return urls

    depth = 0
    end = None
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if not end:
        return urls

    obj_text = text[start:end]
    try:
        import json

        image_info = json.loads(obj_text)
    except Exception:
        return urls

    display_images = image_info.get("displayImages") or []
    if isinstance(display_images, list):
        for img in display_images:
            if not isinstance(img, dict):
                continue
            url_list = img.get("urlList") or []
            if isinstance(url_list, list):
                for u in url_list:
                    _add_url(urls, u, seen)

    return urls


def extract_tiktok_info(url: str) -> Optional[Dict]:
    clean_url = url.split("?", 1)[0].strip()
    clean_url = re.sub(r"/photo/(\d+)", r"/video/\1", clean_url)
    item_match = re.search(r"/(photo|video)/(\d+)", clean_url)
    item_id = item_match.group(2) if item_match else ""

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "dump_single_json": True,
        "user_agent": get_random_user_agent(),
        "nocheckcertificate": True,
    }

    proxy = get_proxy()
    if proxy:
        ydl_opts["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Extracting info for URL: %s", clean_url)
            info = ydl.extract_info(clean_url, download=False)

            if not info:
                return None

            if os.getenv("DEBUG_TIKTOK") == "1":
                try:
                    debug_path = os.path.join(os.getcwd(), "tiktok_debug.json")
                    with open(debug_path, "w", encoding="utf-8") as f:
                        import json
                        json.dump(info, f, ensure_ascii=False, indent=2)
                    logger.info("Wrote debug JSON: %s", debug_path)
                except Exception as e:
                    logger.error("Failed to write tiktok_debug.json: %s", e)

            result = {
                "id": info.get("id"),
                "title": info.get("title", ""),
                "author": info.get("uploader", ""),
                "music": _extract_audio(info),
                "images": _extract_images(info),
                "video": None,
                "type": "unknown",
                "thumbnail": info.get("thumbnail"),
            }

            if info.get("url"):
                result["type"] = "video"
                result["video"] = info.get("url")

            if info.get("_type") == "playlist" or result["images"]:
                result["type"] = "slideshow"

            embed_images = []
            if item_id:
                embed_images = _extract_images_from_embed(item_id)
                if embed_images:
                    if not result["images"] or len(embed_images) > len(result["images"]):
                        result["images"] = embed_images
                        result["type"] = "slideshow"

            return result

    except Exception as e:
        logger.error("Extract error: %s", e)
        return None
