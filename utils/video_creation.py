import os
import numpy as np
from PIL import Image
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
)
from config import FPS, VIDEO_CODEC, AUDIO_CODEC
from utils.audio_generation import get_voice_duration

# Thời lượng chuyển cảnh (giây)
TRANSITION_DURATION = 0.5


def create_video(image_paths, audio_paths, output_path, fps=None,
                 use_transitions=False, add_background_music=False):
    """
    Tạo video, ghép hình ảnh và âm thanh thành video.

    Args:
        image_paths (list): Danh sách đường dẫn tệp hình ảnh
        audio_paths (list): Danh sách đường dẫn tệp âm thanh, phần tử có thể là None
        output_path (str): Đường dẫn tệp video đầu ra
        fps (int): Tốc độ khung hình, mặc định dùng FPS trong cấu hình
        use_transitions (bool): Có dùng hiệu ứng chuyển cảnh (làm mờ dần) hay không
        add_background_music (bool): Có thêm nhạc nền hay không

    Returns:
        str: Đường dẫn tệp video đầu ra, thất bại trả về None
    """
    if fps is None:
        fps = FPS

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    video_clips = []

    for i, image_path in enumerate(image_paths):
        # Nạp hình ảnh
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
        except Exception as e:
            print(f"Nạp hình ảnh thất bại {image_path}: {e}")
            img_array = np.full((384, 512, 3), 255, dtype=np.uint8)

        # Xác định thời lượng đoạn
        duration = 3.0
        has_audio = audio_paths and i < len(audio_paths) and audio_paths[i]
        if has_audio:
            duration = max(get_voice_duration(audio_paths[i]), 2.0)

        # Tạo đoạn hình ảnh
        image_clip = ImageClip(img_array).set_duration(duration)

        # Thêm chuyển cảnh (làm mờ dần), đoạn đầu tiên không thêm
        if use_transitions and i > 0:
            image_clip = image_clip.crossfadein(TRANSITION_DURATION)

        # Thêm âm thanh
        if has_audio:
            try:
                audio_clip = AudioFileClip(audio_paths[i])
                image_clip = image_clip.set_audio(audio_clip)
            except Exception as e:
                print(f"Nạp âm thanh thất bại {audio_paths[i]}: {e}")

        video_clips.append(image_clip)

    if not video_clips:
        print("Không có đoạn video khả dụng")
        return None

    # Ghép tất cả các đoạn
    try:
        if use_transitions and len(video_clips) > 1:
            final_clip = concatenate_videoclips(
                video_clips, method="compose", padding=-TRANSITION_DURATION
            )
        else:
            final_clip = concatenate_videoclips(video_clips, method="compose")
    except Exception as e:
        print(f"Ghép các đoạn video thất bại: {e}")
        return None

    # Thêm nhạc nền
    if add_background_music:
        try:
            bg_music_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'static', 'audio', 'background.mp3'
            )
            if os.path.exists(bg_music_path):
                bg_music = AudioFileClip(bg_music_path)

                # Khớp với độ dài video
                if bg_music.duration < final_clip.duration:
                    bg_music = bg_music.audio_loop(duration=final_clip.duration)
                else:
                    bg_music = bg_music.subclip(0, final_clip.duration)

                # Giảm âm lượng nhạc nền
                bg_music = bg_music.volumex(0.3)

                # Trộn âm thanh gốc và nhạc nền
                if final_clip.audio is not None:
                    final_audio = CompositeAudioClip([final_clip.audio, bg_music])
                    final_clip = final_clip.set_audio(final_audio)
                else:
                    final_clip = final_clip.set_audio(bg_music)
            else:
                print(f"Tệp nhạc nền không tồn tại, bỏ qua: {bg_music_path}")
        except Exception as e:
            print(f"Thêm nhạc nền thất bại: {e}")

    # Ghi tệp video
    try:
        final_clip.write_videofile(
            output_path,
            fps=fps,
            codec=VIDEO_CODEC,
            audio_codec=AUDIO_CODEC,
            threads=4,
            preset='medium',
        )
    except Exception as e:
        print(f"Ghi video thất bại: {e}")
        return None
    finally:
        try:
            final_clip.close()
        except Exception:
            pass

    return output_path


def create_video_from_images_and_audio(image_paths, audio_paths, output_path, fps=None):
    """Hàm tương thích, gọi create_video."""
    return create_video(image_paths, audio_paths, output_path, fps)
