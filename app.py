import os
import time
import uuid
import threading
import logging
import shutil
import random
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from utils.text_processing import (
    split_text_into_scenes,
    generate_scene_descriptions,
    generate_prompts,
    generate_negative_prompts,
)
from utils.image_generation import get_pipeline, generate_images_for_scenes
from utils.audio_generation import generate_audio_for_scenes, get_available_voices
from utils.video_creation import create_video
import config

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Tạo ứng dụng Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Giới hạn tải lên 10MB
CORS(app)

# Từ điển tác vụ toàn cục, dùng để theo dõi trạng thái tác vụ
tasks = {}

# Đảm bảo các thư mục đầu ra tồn tại
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
os.makedirs(config.STATIC_FOLDER, exist_ok=True)
os.makedirs(config.TEMPLATE_FOLDER, exist_ok=True)

# Nạp trước mô hình Stable Diffusion trong luồng nền (lần đầu sẽ tải ~4GB)
threading.Thread(target=get_pipeline, daemon=True).start()

# Route trang chủ
@app.route('/')
def index():
    # Lấy danh sách giọng nói khả dụng
    voices = get_available_voices()
    # Lấy các phong cách truyện tranh khả dụng
    styles = config.COMIC_STYLES
    return render_template('index.html', voices=voices, styles=styles)

# Cung cấp quyền truy cập tệp video đầu ra
@app.route('/outputs/<path:filename>')
def serve_output(filename):
    return send_from_directory(config.OUTPUT_FOLDER, filename)

# Route API - tạo video truyện tranh
@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        # Lấy dữ liệu yêu cầu
        data = request.json
        text = data.get('text', '')
        style = data.get('style', 'default')
        voice = data.get('voice', config.DEFAULT_VOICE)
        use_transitions = data.get('use_transitions', True)  # Có dùng hiệu ứng chuyển cảnh hay không
        add_background_music = data.get('add_background_music', False)  # Có thêm nhạc nền hay không

        # Kiểm tra đầu vào
        if not text:
            return jsonify({'error': 'Vui lòng cung cấp nội dung văn bản'}), 400

        if len(text) > config.MAX_TEXT_LENGTH:
            return jsonify({'error': f'Độ dài văn bản vượt quá giới hạn ({config.MAX_TEXT_LENGTH} ký tự)'}), 400

        # Tạo ID tác vụ
        task_id = str(uuid.uuid4())

        # Tạo thư mục đầu ra cho tác vụ
        task_output_folder = os.path.join(config.OUTPUT_FOLDER, task_id)
        os.makedirs(task_output_folder, exist_ok=True)

        # Khởi tạo trạng thái tác vụ
        tasks[task_id] = {
            'status': 'processing',
            'progress': 0,
            'start_time': time.time(),
            'output_folder': task_output_folder,
            'text': text[:100] + '...' if len(text) > 100 else text,  # Lưu văn bản đã cắt ngắn để ghi lịch sử
            'style': style
        }

        # Lưu ID tác vụ gần đây trong phiên
        if 'recent_tasks' not in session:
            session['recent_tasks'] = []

        recent_tasks = session['recent_tasks']
        if task_id not in recent_tasks:
            recent_tasks.insert(0, task_id)

        # Chỉ giữ lại 10 tác vụ gần nhất
        session['recent_tasks'] = recent_tasks[:10]

        # Khởi động luồng xử lý nền
        threading.Thread(target=process_task, args=(task_id, text, style, voice, use_transitions, add_background_music)).start()

        # Trả về ID tác vụ
        return jsonify({
            'task_id': task_id,
            'status': 'processing'
        })

    except Exception as e:
        logger.error(f"Xử lý thất bại: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Tác vụ xử lý nền
def process_task(task_id, text, style, voice, use_transitions=True, add_background_music=False):
    try:
        task_output_folder = tasks[task_id]['output_folder']

        # Xử lý văn bản - phân tách thành các cảnh
        logger.info(f"Xử lý văn bản, ID tác vụ: {task_id}")
        scenes = split_text_into_scenes(text, max_scenes=config.MAX_SCENES)
        descriptions = generate_scene_descriptions(scenes)
        tasks[task_id]['progress'] = 10

        # Tạo prompt
        logger.info(f"Tạo prompt, ID tác vụ: {task_id}")
        prompts = generate_prompts(descriptions, style)
        negative_prompt = generate_negative_prompts(style)
        tasks[task_id]['progress'] = 20

        # Tạo hình ảnh
        logger.info(f"Tạo hình ảnh, ID tác vụ: {task_id}")
        image_paths = generate_images_for_scenes(prompts, negative_prompt, task_output_folder, style)
        tasks[task_id]['progress'] = 60

        # Tạo âm thanh
        logger.info(f"Tạo âm thanh, ID tác vụ: {task_id}")
        audio_paths = generate_audio_for_scenes(scenes, task_output_folder, voice)
        tasks[task_id]['progress'] = 80

        # Tạo video
        logger.info(f"Tạo video, ID tác vụ: {task_id}")
        output_path = os.path.join(task_output_folder, 'output.mp4')
        video_path = create_video(
            image_paths,
            audio_paths,
            output_path,
            use_transitions=use_transitions,
            add_background_music=add_background_music,
        )

        if not video_path:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = 'Tạo video thất bại'
            return

        # Cập nhật trạng thái tác vụ
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['video_url'] = f'/outputs/{task_id}/output.mp4'
        tasks[task_id]['completion_time'] = time.time()

    except Exception as e:
        logger.error(f"Xử lý tác vụ thất bại: {str(e)}")
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = str(e)

# Route API - lấy trạng thái tác vụ
@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Tác vụ không tồn tại'}), 404
    
    task = tasks[task_id]
    response = {
        'status': task['status'],
        'progress': task['progress']
    }
    
    if task['status'] == 'completed':
        response['video_url'] = task['video_url']
    elif task['status'] == 'failed':
        response['error'] = task.get('error', 'Lỗi không xác định')

    return jsonify(response)

# Route API - lấy các tác vụ trong lịch sử
@app.route('/api/history', methods=['GET'])
def get_history():
    # Lấy 10 tác vụ gần nhất
    recent_tasks = []
    for task_id, task in sorted(tasks.items(), key=lambda x: x[1].get('start_time', 0), reverse=True)[:10]:
        recent_tasks.append({
            'task_id': task_id,
            'text': task.get('text', ''),
            'style': task.get('style', ''),
            'status': task.get('status', ''),
            'start_time': task.get('start_time', 0),
            'completion_time': task.get('completion_time', 0) if task.get('status') == 'completed' else 0
        })
    
    return jsonify(recent_tasks)

# Route API - lấy các giọng nói khả dụng
@app.route('/api/voices', methods=['GET'])
def get_voices():
    voices = get_available_voices()
    return jsonify({'voices': voices})

# Dọn dẹp các tác vụ cũ
def cleanup_tasks():
    # Kích hoạt dọn dẹp ngẫu nhiên, tránh kiểm tra ở mỗi lần yêu cầu
    if random.random() < 0.01:  # Xác suất 1% kích hoạt dọn dẹp
        current_time = time.time()
        to_remove = []

        for task_id, task in tasks.items():
            # Dọn dẹp các tác vụ quá 24 giờ
            if current_time - task.get('start_time', current_time) > 86400:  # 24 giờ = 86400 giây
                to_remove.append(task_id)
                # Xoá thư mục đầu ra của tác vụ
                task_output_folder = task.get('output_folder')
                if task_output_folder and os.path.exists(task_output_folder):
                    try:
                        shutil.rmtree(task_output_folder)
                    except Exception as e:
                        logger.error(f"Xoá thư mục tác vụ thất bại: {str(e)}")

        # Xoá khỏi từ điển tác vụ
        for task_id in to_remove:
            tasks.pop(task_id, None)

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
