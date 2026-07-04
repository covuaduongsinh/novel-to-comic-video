import os
import re
import time
import tempfile
import requests
from config import VBEE_APP_ID, VBEE_ACCESS_TOKEN, DEFAULT_VOICE

# Điểm cuối API Vbee TTS
VBEE_TTS_URL = "https://api.vbee.vn/v1/tts"
VBEE_VOICES_URL = "https://vbee.vn/api/public/v1/voices"

# Số ký tự tối đa mỗi yêu cầu cho giao diện đồng bộ Vbee (chừa chút dư, giới hạn chính thức là 300)
MAX_CHARS_PER_REQUEST = 290


def _get_headers():
    """Xây dựng header xác thực cho API Vbee"""
    return {
        "Authorization": f"Bearer {VBEE_ACCESS_TOKEN}",
        "App-Id": VBEE_APP_ID,
        "Content-Type": "application/json",
    }


def _split_text_for_tts(text, max_chars=MAX_CHARS_PER_REQUEST):
    """
    Cắt văn bản theo ranh giới câu thành các đoạn không quá max_chars, dùng cho giao diện đồng bộ Vbee.

    Args:
        text (str): Văn bản đầu vào
        max_chars (int): Số ký tự tối đa mỗi đoạn

    Returns:
        list: Danh sách các đoạn văn bản
    """
    text = text.strip()
    if not text:
        return []

    # Nếu tổng thể không vượt giới hạn, trả về ngay
    if len(text) <= max_chars:
        return [text]

    # Cắt theo dấu câu cuối câu tiếng Trung/tiếng Anh, giữ lại dấu câu
    sentences = re.findall(r'[^。！？\.!?]+[。！？\.!?]?', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = ""
    for sentence in sentences:
        # Bản thân một câu đã vượt giới hạn, cắt cứng thêm theo ký tự
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(sentence), max_chars):
                chunks.append(sentence[i:i + max_chars])
            continue

        # Cộng dồn theo kiểu tham lam cho đến khi gần chạm giới hạn
        if len(current) + len(sentence) <= max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def _synthesize_chunk(text, voice_name, speed=1.0):
    """
    Gọi giao diện đồng bộ Vbee để tổng hợp một đoạn văn bản, trả về dữ liệu byte MP3.

    Args:
        text (str): Đoạn văn bản (<= 290 ký tự)
        voice_name (str): Mã giọng Vbee
        speed (float): Tốc độ nói 0.25-1.9

    Returns:
        bytes or None: Thành công trả về byte MP3, thất bại trả về None
    """
    payload = {
        "text": text,
        "mode": "sync",
        "voiceCode": voice_name,
        "outputFormat": "mp3",
        "bitrate": 128,
        "speed": speed,
    }

    try:
        response = requests.post(
            VBEE_TTS_URL,
            headers=_get_headers(),
            json=payload,
            timeout=60,
        )
    except Exception as e:
        print(f"Yêu cầu Vbee thất bại: {e}")
        return None

    content_type = response.headers.get("Content-Type", "")

    # Khi thành công trả về nhị phân âm thanh; khi thất bại trả về lỗi JSON
    if response.status_code == 200 and "application/json" not in content_type:
        return response.content

    # Phân tích thông tin lỗi
    try:
        err = response.json()
        print(f"Tổng hợp Vbee thất bại (HTTP {response.status_code}): {err}")
    except Exception:
        print(f"Tổng hợp Vbee thất bại (HTTP {response.status_code}): {response.text[:200]}")
    return None


def generate_speech(text, output_path, voice_name=None, speed=1.0):
    """
    Dùng dịch vụ giọng nói Vbee để tạo giọng nói (tự động chia đoạn và ghép nối).

    Args:
        text (str): Văn bản cần chuyển thành giọng nói
        output_path (str): Đường dẫn tệp âm thanh đầu ra (.mp3)
        voice_name (str): Mã giọng Vbee, mặc định dùng DEFAULT_VOICE trong cấu hình
        speed (float): Điều chỉnh tốc độ nói, phạm vi 0.25-1.9

    Returns:
        bool: Có tạo giọng nói thành công hay không
    """
    # Kiểm tra thông tin xác thực
    if not VBEE_APP_ID or not VBEE_ACCESS_TOKEN:
        print("Lỗi: Chưa cấu hình Vbee APP_ID hoặc ACCESS_TOKEN")
        return False

    if voice_name is None:
        voice_name = DEFAULT_VOICE

    text = (text or "").strip()
    if not text:
        print("Cảnh báo: Văn bản rỗng, bỏ qua tổng hợp giọng nói")
        return False

    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Chia đoạn
    chunks = _split_text_for_tts(text)

    # Tổng hợp từng đoạn
    chunk_bytes = []
    for i, chunk in enumerate(chunks):
        audio = _synthesize_chunk(chunk, voice_name, speed)
        if audio is None:
            print(f"Đoạn {i + 1}/{len(chunks)} tổng hợp thất bại")
            return False
        chunk_bytes.append(audio)
        # Chờ nhẹ, tránh kích hoạt giới hạn tần suất
        if len(chunks) > 1:
            time.sleep(0.3)

    # Nếu chỉ có một đoạn thì ghi tệp trực tiếp; nhiều đoạn thì ghép bằng pydub
    try:
        if len(chunk_bytes) == 1:
            with open(output_path, "wb") as f:
                f.write(chunk_bytes[0])
        else:
            from pydub import AudioSegment
            combined = AudioSegment.empty()
            tmp_files = []
            try:
                for audio in chunk_bytes:
                    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tmp.write(audio)
                    tmp.close()
                    tmp_files.append(tmp.name)
                    combined += AudioSegment.from_file(tmp.name, format="mp3")
                combined.export(output_path, format="mp3")
            finally:
                for p in tmp_files:
                    try:
                        os.remove(p)
                    except OSError:
                        pass
        print(f"Tạo giọng nói thành công: {output_path}")
        return True
    except Exception as e:
        print(f"Ghép/lưu âm thanh thất bại: {e}")
        return False


def generate_audio_for_scenes(scenes, output_dir, voice_name=None):
    """
    Tạo tệp âm thanh cho nhiều cảnh.

    Args:
        scenes (list): Danh sách văn bản các cảnh
        output_dir (str): Thư mục đầu ra
        voice_name (str): Mã giọng

    Returns:
        list: Danh sách đường dẫn tệp âm thanh đã tạo (phần tử thất bại là None)
    """
    os.makedirs(output_dir, exist_ok=True)

    audio_paths = []
    for i, scene in enumerate(scenes):
        audio_path = os.path.join(output_dir, f"scene_{i:03d}.mp3")
        success = generate_speech(
            text=scene,
            output_path=audio_path,
            voice_name=voice_name,
        )

        if success:
            audio_paths.append(audio_path)
            print(f"Tạo âm thanh {i + 1}/{len(scenes)}: {audio_path}")
        else:
            print(f"Tạo âm thanh {i + 1}/{len(scenes)} thất bại")
            audio_paths.append(None)

    return audio_paths


# Danh sách giọng dự phòng dùng khi không có thông tin xác thực hoặc giao diện lỗi
_FALLBACK_VOICES = [
    {"name": "hn_female_ngochuyen_full_48k-fhg", "display_name": "Ngọc Huyền (Nữ - Bắc)", "locale": "vi-VN", "gender": "female"},
    {"name": "hn_male_manhdung_news_48k-fhg", "display_name": "Mạnh Dũng (Nam - Bắc)", "locale": "vi-VN", "gender": "male"},
    {"name": "sg_female_lantrinh_vdts_48k-fhg", "display_name": "Lan Trinh (Nữ - Nam)", "locale": "vi-VN", "gender": "female"},
    {"name": "hue_female_huonggiang_full_48k-fhg", "display_name": "Hương Giang (Nữ - Huế)", "locale": "vi-VN", "gender": "female"},
]


def get_available_voices():
    """
    Lấy danh sách giọng nói khả dụng của Vbee.

    Returns:
        list: Danh sách thông tin giọng nói [{name, display_name, locale, gender}, ...]
    """
    if not VBEE_APP_ID or not VBEE_ACCESS_TOKEN:
        print("Cảnh báo: Chưa cấu hình thông tin xác thực Vbee, trả về danh sách giọng dự phòng")
        return _FALLBACK_VOICES

    try:
        response = requests.get(VBEE_VOICES_URL, headers=_get_headers(), timeout=30)
        data = response.json()

        if response.status_code == 200 and data.get("status") == 1:
            result = data.get("result", {})
            voices = []
            for v in result.get("voices", []):
                voices.append({
                    "name": v.get("code"),
                    "display_name": v.get("name", v.get("code")),
                    "locale": v.get("language_code", ""),
                    "gender": v.get("gender", ""),
                })
            return voices if voices else _FALLBACK_VOICES
        else:
            print(f"Lấy danh sách giọng thất bại: {data}")
            return _FALLBACK_VOICES
    except Exception as e:
        print(f"Lấy danh sách giọng thất bại: {e}")
        return _FALLBACK_VOICES


def get_voice_duration(audio_path):
    """
    Lấy thời lượng của tệp âm thanh (giây).

    Args:
        audio_path (str): Đường dẫn tệp âm thanh

    Returns:
        float: Thời lượng âm thanh (giây)
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0  # Đổi mili giây sang giây
    except Exception as e:
        print(f"Lấy thời lượng âm thanh thất bại: {e}")
        # Nếu không lấy được, trả về giá trị ước tính
        try:
            with open(audio_path, 'rb') as f:
                file_size = len(f.read())
                estimated_duration = file_size / 10000
                return max(estimated_duration, 1.0)
        except Exception:
            return 3.0  # Mặc định 3 giây
