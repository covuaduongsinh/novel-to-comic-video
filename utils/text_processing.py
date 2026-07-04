import re
import jieba
import nltk
from nltk.tokenize import sent_tokenize

# Thử tải dữ liệu nltk, nếu đã tồn tại thì bỏ qua
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def split_text_into_scenes(text, max_scenes=10):
    """
    Phân tách văn bản đầu vào thành danh sách các cảnh

    Args:
        text (str): Nội dung văn bản đầu vào
        max_scenes (int): Số cảnh tối đa

    Returns:
        list: Danh sách văn bản các cảnh
    """
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()

    # Phát hiện ngôn ngữ (kiểm tra đơn giản xem có phải tiếng Trung không)
    is_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
    
    if is_chinese:
        # Xử lý văn bản tiếng Trung
        # Tách theo dấu chấm, dấu hỏi, dấu chấm than, giữ lại dấu câu
        sentences = re.findall(r'[^。！？]+[。！？]', text)
        if not sentences and text:
            sentences = [text]  # Nếu tách không thành công thì xem toàn bộ văn bản là một câu
    else:
        # Xử lý văn bản tiếng Anh
        sentences = sent_tokenize(text)

    # Nếu số câu ít hơn max_scenes, trả về mỗi câu là một cảnh
    if len(sentences) <= max_scenes:
        return sentences

    # Gộp các câu thành cảnh, cố gắng phân bổ đều
    scenes = []
    sentences_per_scene = len(sentences) // max_scenes
    remainder = len(sentences) % max_scenes
    
    start_idx = 0
    for i in range(max_scenes):
        # Phân bổ thêm một câu cho remainder cảnh đầu tiên
        end_idx = start_idx + sentences_per_scene + (1 if i < remainder else 0)
        scene = ' '.join(sentences[start_idx:end_idx])
        scenes.append(scene)
        start_idx = end_idx
    
    return scenes

def generate_scene_descriptions(scenes):
    """
    Tạo mô tả cho từng cảnh, dùng để tạo hình ảnh

    Args:
        scenes (list): Danh sách văn bản các cảnh

    Returns:
        list: Danh sách mô tả cảnh, dùng để tạo hình ảnh
    """
    descriptions = []

    for scene in scenes:
        # Loại bỏ khoảng trắng thừa
        scene = re.sub(r'\s+', ' ', scene).strip()

        # Phát hiện ngôn ngữ
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', scene))
        
        if is_chinese:
            # Xử lý cảnh tiếng Trung
            # Dùng jieba để trích xuất từ khoá và cụm từ
            words = jieba.cut(scene)
            # Lọc bỏ từ dừng và dấu câu
            filtered_words = [w for w in words if len(w) > 1 and not re.match(r'[\W\d]+', w)]

            # Trích xuất danh từ và động từ chính làm mô tả
            if filtered_words:
                # Lấy đơn giản 10 từ có nghĩa đầu tiên
                key_terms = filtered_words[:10]
                description = scene if len(scene) < 100 else ' '.join(key_terms)
            else:
                description = scene
        else:
            # Xử lý cảnh tiếng Anh
            # Xử lý đơn giản, dùng trực tiếp văn bản cảnh gốc
            description = scene if len(scene) < 100 else scene[:100] + '...'
        
        descriptions.append(description)
    
    return descriptions

def generate_prompts(scene_descriptions, style="default"):
    """
    Tạo prompt tạo hình ảnh dựa trên mô tả cảnh và phong cách

    Args:
        scene_descriptions (list): Danh sách mô tả cảnh
        style (str): Phong cách truyện tranh

    Returns:
        list: Danh sách prompt
    """
    # Ánh xạ prompt theo phong cách
    style_prompts = {
        'default': ', comic style, detailed, vibrant colors',
        'anime': ', anime style, manga, detailed, vibrant colors',
        'realistic': ', realistic style, detailed, photorealistic',
        'watercolor': ', watercolor style, artistic, soft colors',
        'sketch': ', sketch style, pencil drawing, black and white'
    }
    
    # Lấy prompt phong cách, nếu không tồn tại thì dùng phong cách mặc định
    style_prompt = style_prompts.get(style, style_prompts['default'])

    # Tạo prompt cho từng mô tả cảnh
    prompts = []
    for description in scene_descriptions:
        # Phát hiện ngôn ngữ
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', description))
        
        if is_chinese:
            # Mô tả tiếng Trung, thêm gợi ý dịch sang tiếng Anh
            prompt = f"scene from a story: {description}, illustration{style_prompt}"
        else:
            # Mô tả tiếng Anh
            prompt = f"scene from a story: {description}, illustration{style_prompt}"
        
        prompts.append(prompt)
    
    return prompts

def generate_negative_prompts(style="default"):
    """
    Tạo prompt phủ định dựa trên phong cách

    Args:
        style (str): Phong cách truyện tranh

    Returns:
        str: Prompt phủ định
    """
    # Ánh xạ prompt phủ định theo phong cách
    style_negative_prompts = {
        'default': 'blurry, low quality, distorted, deformed',
        'anime': 'blurry, low quality, distorted, deformed, photorealistic',
        'realistic': 'cartoon, anime, sketch, drawing, blurry',
        'watercolor': 'digital art, sharp edges, blurry, low quality',
        'sketch': 'color, painting, digital art, blurry, low quality'
    }
    
    # Lấy prompt phủ định theo phong cách, nếu không tồn tại thì dùng phong cách mặc định
    negative_prompt = style_negative_prompts.get(style, style_negative_prompts['default'])

    # Thêm prompt phủ định dùng chung
    common_negative = "text, watermark, signature, logo, nsfw, nude, bad anatomy, bad hands, extra fingers"
    
    return f"{negative_prompt}, {common_negative}"
