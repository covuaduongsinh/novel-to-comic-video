/**
 * Ứng dụng chuyển tiểu thuyết thành video truyện tranh - Kịch bản tương tác giao diện
 */

// Thực thi sau khi tài liệu tải xong
document.addEventListener('DOMContentLoaded', function() {
    // Lấy các phần tử DOM
    const generateForm = document.getElementById('generate-form');
    const storyInput = document.getElementById('story-text');
    const charCounter = document.getElementById('char-counter');
    const maxChars = parseInt(storyInput.getAttribute('maxlength') || 2000);
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const resultContainer = document.getElementById('result-container');
    const videoPlayer = document.getElementById('video-player');
    const downloadBtn = document.getElementById('download-btn');
    const newGenerationBtn = document.getElementById('new-generation-btn');
    const submitBtn = document.getElementById('submit-btn');
    const voiceSelect = document.getElementById('voice-select');
    
    // ID tác vụ và khoảng thời gian thăm dò
    let taskId = null;
    let pollInterval = null;
    const POLL_FREQUENCY = 3000; // 3 giây

    // Khởi tạo bộ đếm ký tự
    updateCharCounter();

    // Lắng nghe nhập văn bản, cập nhật số ký tự
    storyInput.addEventListener('input', updateCharCounter);

    // Lắng nghe gửi biểu mẫu
    generateForm.addEventListener('submit', function(e) {
        e.preventDefault();
        submitGeneration();
    });

    // Lắng nghe nút tạo mới
    if (newGenerationBtn) {
        newGenerationBtn.addEventListener('click', resetForm);
    }

    // Tải danh sách giọng nói khả dụng
    loadVoices();

    /**
     * Cập nhật bộ đếm ký tự
     */
    function updateCharCounter() {
        const currentLength = storyInput.value.length;
        const remaining = maxChars - currentLength;

        charCounter.textContent = `${currentLength}/${maxChars} ký tự`;

        // Cập nhật kiểu theo số ký tự còn lại
        charCounter.className = 'char-counter';
        if (remaining < maxChars * 0.2) {
            charCounter.classList.add('warning');
        }
        if (remaining < maxChars * 0.1) {
            charCounter.classList.add('danger');
        }
    }
    
    /**
     * Gửi yêu cầu tạo video
     */
    function submitGeneration() {
        // Lấy dữ liệu biểu mẫu
        const formData = new FormData(generateForm);
        const storyText = formData.get('story_text');

        // Kiểm tra đầu vào
        if (!storyText || storyText.trim().length < 10) {
            showAlert('Vui lòng nhập văn bản câu chuyện ít nhất 10 ký tự', 'danger');
            return;
        }

        // Vô hiệu hoá nút gửi, hiển thị trạng thái đang tải
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner"></span> Đang xử lý...';

        // Hiển thị thanh tiến độ, khởi tạo ở 0%
        progressContainer.style.display = 'block';
        updateProgress(0, 'Đang khởi tạo...');

        // Ẩn khu vực kết quả
        resultContainer.style.display = 'none';

        // Gửi yêu cầu API
        axios.post('/api/generate', {
            story_text: storyText,
            comic_style: formData.get('comic_style') || 'default',
            voice_name: formData.get('voice_name') || 'zh-CN-XiaoxiaoNeural',
            use_transitions: formData.get('use_transitions') === 'on',
            add_background_music: formData.get('add_background_music') === 'on'
        })
        .then(function(response) {
            // Lưu ID tác vụ và bắt đầu thăm dò trạng thái
            taskId = response.data.task_id;
            startPolling();
        })
        .catch(function(error) {
            // Xử lý lỗi
            console.error('Gửi yêu cầu tạo video thất bại:', error);
            let errorMessage = 'Gửi yêu cầu tạo video thất bại';
            if (error.response && error.response.data && error.response.data.error) {
                errorMessage = error.response.data.error;
            }
            showAlert(errorMessage, 'danger');
            resetSubmitButton();
        });
    }

    /**
     * Bắt đầu thăm dò trạng thái tác vụ
     */
    function startPolling() {
        // Xoá thăm dò có thể đang tồn tại
        if (pollInterval) {
            clearInterval(pollInterval);
        }

        // Thiết lập thăm dò mới
        pollInterval = setInterval(function() {
            checkTaskStatus();
        }, POLL_FREQUENCY);

        // Kiểm tra trạng thái ngay một lần
        checkTaskStatus();
    }

    /**
     * Kiểm tra trạng thái tác vụ
     */
    function checkTaskStatus() {
        if (!taskId) return;

        axios.get(`/api/status/${taskId}`)
            .then(function(response) {
                const data = response.data;

                // Cập nhật tiến độ
                updateProgress(data.progress, data.status);

                // Nếu tác vụ hoàn thành
                if (data.state === 'completed') {
                    stopPolling();
                    showResult(data.result);
                    resetSubmitButton();
                }
                // Nếu tác vụ thất bại
                else if (data.state === 'failed') {
                    stopPolling();
                    showAlert(`Tạo video thất bại: ${data.error || 'Lỗi không xác định'}`, 'danger');
                    resetSubmitButton();
                }
            })
            .catch(function(error) {
                console.error('Kiểm tra trạng thái thất bại:', error);
                // Nếu kiểm tra thất bại liên tiếp nhiều lần, có thể dừng thăm dò
                // Ở đây xử lý đơn giản, dừng luôn
                stopPolling();
                showAlert('Không thể lấy trạng thái tác vụ', 'warning');
                resetSubmitButton();
            });
    }

    /**
     * Dừng thăm dò
     */
    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }
    
    /**
     * Cập nhật thanh tiến độ
     */
    function updateProgress(percent, statusText) {
        // Đảm bảo phần trăm nằm trong khoảng 0-100
        percent = Math.min(100, Math.max(0, percent));

        // Cập nhật thanh tiến độ
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);

        // Cập nhật văn bản trạng thái
        if (statusText) {
            progressText.textContent = `${statusText} (${Math.round(percent)}%)`;
        } else {
            progressText.textContent = `${Math.round(percent)}%`;
        }
    }

    /**
     * Hiển thị kết quả
     */
    function showResult(result) {
        if (!result || !result.video_url) {
            showAlert('Kết quả tạo video không hợp lệ', 'danger');
            return;
        }

        // Hiển thị vùng chứa kết quả
        resultContainer.style.display = 'block';
        resultContainer.classList.add('fade-in');

        // Thiết lập trình phát video
        videoPlayer.src = result.video_url;
        videoPlayer.poster = result.thumbnail_url || '';
        videoPlayer.load();

        // Thiết lập liên kết tải xuống
        if (downloadBtn) {
            downloadBtn.href = result.video_url;
            downloadBtn.download = result.filename || 'comic-video.mp4';
        }

        // Cuộn đến khu vực kết quả
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Đặt lại biểu mẫu
     */
    function resetForm() {
        // Dừng mọi thăm dò đang diễn ra
        stopPolling();

        // Đặt lại biểu mẫu
        generateForm.reset();

        // Cập nhật số ký tự
        updateCharCounter();

        // Đặt lại nút gửi
        resetSubmitButton();

        // Ẩn tiến độ và kết quả
        progressContainer.style.display = 'none';
        resultContainer.style.display = 'none';

        // Cuộn lên đầu biểu mẫu
        generateForm.scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Đặt lại trạng thái nút gửi
     */
    function resetSubmitButton() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Tạo video truyện tranh';
    }

    /**
     * Hiển thị thông báo cảnh báo/nhắc nhở
     */
    function showAlert(message, type = 'info') {
        // Tạo phần tử cảnh báo
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Đóng"></button>
        `;

        // Tìm vùng chứa cảnh báo
        const alertContainer = document.getElementById('alert-container');
        if (alertContainer) {
            // Thêm vào vùng chứa
            alertContainer.appendChild(alertDiv);

            // Tự động đóng sau 5 giây
            setTimeout(() => {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.remove(), 150);
            }, 5000);
        } else {
            // Nếu không có vùng chứa, dùng console
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    /**
     * Tải danh sách giọng nói khả dụng
     */
    function loadVoices() {
        // Nếu không có bộ chọn giọng nói thì trả về ngay
        if (!voiceSelect) return;

        // Hiển thị đang tải
        voiceSelect.innerHTML = '<option value="">Đang tải...</option>';

        // Yêu cầu danh sách giọng nói
        axios.get('/api/voices')
            .then(function(response) {
                const voices = response.data.voices || [];

                // Nếu không có giọng nói, hiển thị thông báo
                if (voices.length === 0) {
                    voiceSelect.innerHTML = '<option value="">Không có giọng nói khả dụng</option>';
                    return;
                }

                // Xoá bộ chọn
                voiceSelect.innerHTML = '';

                // Thêm các tuỳ chọn giọng nói
                voices.forEach(voice => {
                    const option = document.createElement('option');
                    option.value = voice.name;
                    option.textContent = `${voice.display_name} (${voice.locale})`;
                    // Nếu là giọng nói mặc định, đặt làm được chọn
                    if (voice.name === 'zh-CN-XiaoxiaoNeural') {
                        option.selected = true;
                    }
                    voiceSelect.appendChild(option);
                });
            })
            .catch(function(error) {
                console.error('Lấy danh sách giọng nói thất bại:', error);
                voiceSelect.innerHTML = '<option value="zh-CN-XiaoxiaoNeural">Xiaoxiao (Tiếng Trung)</option>';
            });
    }
});
