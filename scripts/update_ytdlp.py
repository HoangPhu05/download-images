import subprocess
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    filename='update_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def update_ytdlp():
    try:
        logging.info("Bắt đầu cập nhật yt-dlp...")
        # Chạy lệnh pip install --upgrade yt-dlp
        result = subprocess.run(
            ["pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            check=True
        )
        logging.info(f"Kết quả cập nhật:\n{result.stdout}")
        print("Cập nhật thành công!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Lỗi khi cập nhật yt-dlp: {e.stderr}")
        print("Cập nhật thất bại. Kiểm tra log.")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Đang chạy update script...")
    update_ytdlp()
