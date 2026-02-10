document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('urlInput');
    const downloadBtn = document.getElementById('downloadBtn');
    const pasteBtn = document.getElementById('pasteBtn');
    const resultSection = document.getElementById('resultSection');
    const gallery = document.getElementById('gallery');
    const videoContainer = document.getElementById('videoContainer');
    const videoPlayer = document.getElementById('videoPlayer');
    const errorMsg = document.getElementById('errorMsg');
    const btnText = document.querySelector('.btn-text');
    const loader = document.querySelector('.loader');
    
    // Auth Info Elements
    const avatar = document.getElementById('avatar');
    const authorName = document.getElementById('authorName');
    const videoTitle = document.getElementById('videoTitle');
    
    // Action Buttons
    const downloadAllBtn = document.getElementById('downloadAllBtn');
    const downloadAudioBtn = document.getElementById('downloadAudioBtn');
    const newDownloadBtn = document.getElementById('newDownloadBtn');

    // Mode Toggle Buttons
    const modeImageBtn = document.getElementById('modeImage');
    const modeAudioBtn = document.getElementById('modeAudio');
    
    // Audio Mode Elements
    const audioResults = document.getElementById('audioResults');
    const convertMp3Btn = document.getElementById('convertMp3Btn');
    const musicDownloadItem = document.getElementById('musicDownloadItem');

    let currentData = null;
    let currentUrl = ''; // Store current URL for conversion
    let currentMode = 'image'; // 'image' or 'audio'

    // Helper function to sanitize filename
    function sanitizeFilename(name, maxLength = 100) {
        if (!name) return 'tiktok';
        // Remove special characters that are not allowed in filenames
        let clean = name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
                       .replace(/[\s]+/g, '_')
                       .trim();
        // Truncate if too long
        if (clean.length > maxLength) {
            clean = clean.substring(0, maxLength);
        }
        return clean || 'tiktok';
    }

    // Mode Toggle Logic
    modeImageBtn.addEventListener('click', () => {
        currentMode = 'image';
        modeImageBtn.classList.add('active');
        modeAudioBtn.classList.remove('active');
        // Reset results when switching mode
        resultSection.classList.add('hidden');
    });

    modeAudioBtn.addEventListener('click', () => {
        currentMode = 'audio';
        modeAudioBtn.classList.add('active');
        modeImageBtn.classList.remove('active');
        // Reset results when switching mode
        resultSection.classList.add('hidden');
    });

    // Paste Button Logic
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text;
        } catch (err) {
            console.error('Failed to read clipboard', err);
        }
    });

    // Main Download Logic
    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showError("Vui lòng nhập đường dẫn TikTok!");
            return;
        }

        // Reset UI
        showError("");
        resultSection.classList.add('hidden');
        setLoading(true);
        currentUrl = url; // Save for MP3 conversion

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Có lỗi xảy ra");
            }

            const data = await response.json();
            currentData = data;
            renderResult(data);

        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    // Reset for new download
    newDownloadBtn.addEventListener('click', () => {
        urlInput.value = "";
        resultSection.classList.add('hidden');
        urlInput.focus();
    });

    // Download All (ZIP) Logic
    downloadAllBtn.addEventListener('click', async () => {
        if (!currentData || !currentData.images || currentData.images.length === 0) return;
        
        // Trigger download
        // We do a fetch to get blob, then create anchor tag
        downloadAllBtn.innerHTML = '<div class="loader" style="width:15px;height:15px;border-width:2px"></div> Đang nén...';
        
        try {
            const zipFilename = sanitizeFilename(currentData.title) + '.zip';
            const response = await fetch('/api/download-zip', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ urls: currentData.images, filename: zipFilename })
            });

            if (!response.ok) throw new Error("Lỗi khi tải zip");

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = zipFilename;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (e) {
            alert("Lỗi tải xuống: " + e.message);
        } finally {
            downloadAllBtn.innerHTML = '<i data-feather="download-cloud"></i> Tải Tất Cả (ZIP)';
            feather.replace();
        }
    });

    // Convert to MP3 Logic
    convertMp3Btn.addEventListener('click', async () => {
        if (!currentUrl) {
            showError("Không có URL để chuyển đổi");
            return;
        }

        const originalContent = convertMp3Btn.innerHTML;
        convertMp3Btn.innerHTML = '<div class="loader" style="width:15px;height:15px;border-width:2px"></div> Đang chuyển đổi...';
        convertMp3Btn.disabled = true;

        try {
            const response = await fetch('/api/convert-mp3', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentUrl })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Lỗi chuyển đổi");
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            
            // Get filename from Content-Disposition header if available
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'tiktok_audio.mp3';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename=(.+)/);
                if (match) {
                    filename = match[1].replace(/"/g, '');
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);
        } catch (e) {
            showError("Lỗi chuyển đổi: " + e.message);
        } finally {
            convertMp3Btn.innerHTML = originalContent;
            convertMp3Btn.disabled = false;
            feather.replace();
        }
    });

    function renderResult(data) {
        // Populate Meta Info
        authorName.textContent = data.author;
        videoTitle.textContent = data.title;
        if (data.thumbnail) {
            avatar.src = data.thumbnail; 
        }

        // Clear previous content
        gallery.innerHTML = '';
        gallery.classList.add('hidden');
        videoContainer.classList.add('hidden');
        audioResults.classList.add('hidden');
        downloadAllBtn.classList.add('hidden');

        if (currentMode === 'image') {
            // Image Mode - Show slideshow images
            if (data.type === 'slideshow' && data.images && data.images.length > 0) {
                gallery.classList.remove('hidden');

                data.images.forEach((imgUrl, index) => {
                    const item = document.createElement('div');
                    item.className = 'gallery-item';

                    const img = document.createElement('img');
                    img.src = imgUrl;
                    img.alt = `image-${index + 1}`;
                    img.loading = 'lazy';
                    img.onclick = () => window.open(imgUrl, '_blank');

                    const actions = document.createElement('div');
                    actions.className = 'image-actions';

                    const downloadLink = document.createElement('a');
                    // Use proxy endpoint for download with caption as filename
                    const baseFilename = sanitizeFilename(data.title);
                    const proxyUrl = `/api/download-image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(baseFilename + '_' + (index + 1) + '.jpg')}`;
                    downloadLink.href = proxyUrl;
                    downloadLink.className = 'download-btn';
                    downloadLink.textContent = 'Tải xuống';

                    actions.appendChild(downloadLink);
                    item.appendChild(img);
                    item.appendChild(actions);
                    gallery.appendChild(item);
                });
            } else if (data.video) {
                // Show video preview for video posts
                videoContainer.classList.remove('hidden');
                videoPlayer.src = data.video;
            } else {
                showError('Không tìm thấy ảnh trong link này.');
                return;
            }
        } else if (currentMode === 'audio') {
            // Audio Mode - Show MP3 convert button
            audioResults.classList.remove('hidden');
            musicDownloadItem.classList.remove('hidden');
        }

        resultSection.classList.remove('hidden');
        feather.replace(); // Re-init icons
    }

    function setLoading(isLoading) {
        if (isLoading) {
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');
            downloadBtn.disabled = true;
        } else {
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
            downloadBtn.disabled = false;
        }
    }

    function showError(msg) {
        if (!msg) {
            errorMsg.classList.add('hidden');
            errorMsg.textContent = "";
            return;
        }
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }
});
