import os
from dotenv import load_dotenv

# Nạp biến môi trường
load_dotenv()

# Thiết lập cơ bản
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Đường dẫn tệp
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')

# Khoá API
HF_API_KEY = os.getenv('HF_API_KEY', '')

# Thông tin xác thực Vbee TTS
VBEE_APP_ID = os.getenv('VBEE_APP_ID', '')
VBEE_ACCESS_TOKEN = os.getenv('VBEE_ACCESS_TOKEN', '')

# Tham số tạo hình ảnh
IMAGE_WIDTH = int(os.getenv('IMAGE_WIDTH', 512))
IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 384))
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'stable-diffusion-v1-5/stable-diffusion-v1-5')

# Tinh chỉnh hiệu năng CPU (khi không có GPU thì giảm số bước suy luận và số cảnh để tạo nhanh hơn)
NUM_INFERENCE_STEPS = int(os.getenv('NUM_INFERENCE_STEPS', 20))
MAX_SCENES = int(os.getenv('MAX_SCENES', 5))

# Tham số tạo video
FPS = int(os.getenv('FPS', 24))
VIDEO_CODEC = os.getenv('VIDEO_CODEC', 'libx264')
AUDIO_CODEC = os.getenv('AUDIO_CODEC', 'aac')

# Giọng nói mặc định (mã giọng Vbee)
DEFAULT_VOICE = os.getenv('DEFAULT_VOICE', 'hn_female_ngochuyen_full_48k-fhg')

# Phong cách truyện tranh
COMIC_STYLES = {
    'default': 'Phong cách truyện tranh mặc định',
    'anime': 'Phong cách anime',
    'realistic': 'Phong cách tả thực',
    'watercolor': 'Phong cách màu nước',
    'sketch': 'Phong cách ký hoạ'
}

# Prompt phong cách
STYLE_PROMPTS = {
    'default': ', comic style, detailed, vibrant colors',
    'anime': ', anime style, manga, detailed, vibrant colors',
    'realistic': ', realistic style, detailed, photorealistic',
    'watercolor': ', watercolor style, artistic, soft colors',
    'sketch': ', sketch style, pencil drawing, black and white'
}

# Prompt phủ định theo phong cách
STYLE_NEGATIVE_PROMPTS = {
    'default': 'blurry, low quality, distorted, deformed',
    'anime': 'blurry, low quality, distorted, deformed, photorealistic',
    'realistic': 'cartoon, anime, sketch, drawing, blurry',
    'watercolor': 'digital art, sharp edges, blurry, low quality',
    'sketch': 'color, painting, digital art, blurry, low quality'
}

# Giới hạn hệ thống
MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', 5000))
CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 3600))  # 1 giờ
TASK_TIMEOUT = int(os.getenv('TASK_TIMEOUT', 600))  # 10 phút

# Lớp cấu hình môi trường
class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = SECRET_KEY

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# Ánh xạ cấu hình
config_by_name = {
    'dev': DevelopmentConfig,
    'test': TestingConfig,
    'prod': ProductionConfig
}

# Lấy cấu hình hiện tại
def get_config():
    env = os.getenv('FLASK_ENV', 'dev')
    return config_by_name.get(env, DevelopmentConfig)
