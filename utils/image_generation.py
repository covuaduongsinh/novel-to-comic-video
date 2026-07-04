import os
import torch
import numpy as np
from PIL import Image
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from config import IMAGE_WIDTH, IMAGE_HEIGHT, DEFAULT_MODEL, HF_API_KEY, NUM_INFERENCE_STEPS

# Kiểm tra xem có GPU khả dụng không
device = "cuda" if torch.cuda.is_available() else "cpu"

# Bộ nhớ đệm mô hình
pipeline_cache = {}

def get_pipeline(model_id=None):
    """
    Lấy hoặc nạp pipeline mô hình Stable Diffusion

    Args:
        model_id (str): ID mô hình, mặc định dùng DEFAULT_MODEL trong cấu hình

    Returns:
        StableDiffusionPipeline: Pipeline mô hình đã nạp
    """
    if model_id is None:
        model_id = DEFAULT_MODEL

    # Nếu mô hình đã được nạp, trả về pipeline trong bộ nhớ đệm
    if model_id in pipeline_cache:
        return pipeline_cache[model_id]

    # Nạp mô hình
    try:
        # HF token tùy chọn (bản diffusers mới dùng tham số token=)
        token = HF_API_KEY if HF_API_KEY else None

        # Dùng DPMSolverMultistepScheduler để cân bằng chất lượng và tốc độ tốt hơn
        scheduler = DPMSolverMultistepScheduler.from_pretrained(
            model_id,
            subfolder="scheduler",
            token=token
        )

        # Môi trường CPU dùng float32 (mặc định), GPU dùng float16 để tiết kiệm VRAM
        torch_dtype = torch.float16 if device == "cuda" else torch.float32

        pipeline = StableDiffusionPipeline.from_pretrained(
            model_id,
            scheduler=scheduler,
            torch_dtype=torch_dtype,
            use_safetensors=True,   # Chỉ dùng safetensors đã lưu đệm, tránh tải lại trọng số .bin trùng lặp
            token=token
        )

        # Chuyển sang thiết bị
        pipeline = pipeline.to(device)

        # Bật attention slicing để giảm mức sử dụng bộ nhớ
        if hasattr(pipeline, "enable_attention_slicing"):
            pipeline.enable_attention_slicing()

        # Nếu là thiết bị CUDA, bật attention tiết kiệm bộ nhớ
        if device == "cuda" and hasattr(pipeline, "enable_xformers_memory_efficient_attention"):
            try:
                pipeline.enable_xformers_memory_efficient_attention()
            except Exception as e:
                print(f"Không thể bật tối ưu hoá xformers: {e}")

        # Lưu pipeline vào bộ nhớ đệm
        pipeline_cache[model_id] = pipeline

        return pipeline
    except Exception as e:
        print(f"Nạp mô hình thất bại: {e}")
        # Nếu nạp thất bại, thử dùng mô hình mặc định
        if model_id != DEFAULT_MODEL:
            print(f"Thử nạp mô hình mặc định: {DEFAULT_MODEL}")
            return get_pipeline(DEFAULT_MODEL)
        raise

def generate_image(prompt, negative_prompt=None, width=None, height=None, model_id=None, seed=None):
    """
    Tạo hình ảnh dựa trên prompt

    Args:
        prompt (str): Prompt tạo hình ảnh
        negative_prompt (str): Prompt phủ định
        width (int): Chiều rộng hình ảnh
        height (int): Chiều cao hình ảnh
        model_id (str): ID mô hình
        seed (int): Hạt giống ngẫu nhiên

    Returns:
        PIL.Image: Hình ảnh đã tạo
    """
    # Dùng giá trị mặc định trong cấu hình
    if width is None:
        width = IMAGE_WIDTH
    if height is None:
        height = IMAGE_HEIGHT

    # Lấy pipeline mô hình
    pipeline = get_pipeline(model_id)

    # Thiết lập hạt giống ngẫu nhiên
    if seed is None:
        seed = np.random.randint(0, 2147483647)
    generator = torch.Generator(device=device).manual_seed(seed)

    # Tạo hình ảnh
    with torch.no_grad():
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=NUM_INFERENCE_STEPS,  # Số bước suy luận, ảnh hưởng chất lượng và tốc độ
            guidance_scale=7.5,      # Cường độ dẫn hướng của prompt
            generator=generator
        )

    # Trả về hình ảnh đã tạo
    image = result.images[0]

    # Ghi lại thông tin tạo ảnh
    generation_info = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "model_id": model_id or DEFAULT_MODEL,
        "seed": seed
    }
    
    return image, generation_info

def generate_images_for_scenes(prompts, negative_prompt, output_dir, style="default", model_id=None):
    """
    Tạo hình ảnh cho nhiều cảnh

    Args:
        prompts (list): Danh sách prompt
        negative_prompt (str): Prompt phủ định
        output_dir (str): Thư mục đầu ra
        style (str): Phong cách truyện tranh
        model_id (str): ID mô hình

    Returns:
        list: Danh sách đường dẫn tệp hình ảnh đã tạo
    """
    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(output_dir, exist_ok=True)

    # Điều chỉnh kích thước hình ảnh theo phong cách
    width, height = IMAGE_WIDTH, IMAGE_HEIGHT
    if style == "anime":
        # Phong cách anime thường dùng tỉ lệ 16:9
        width, height = 768, 432
    elif style == "sketch":
        # Phong cách ký hoạ dùng hình vuông
        width, height = 512, 512

    # Tạo hình ảnh
    image_paths = []
    for i, prompt in enumerate(prompts):
        try:
            # Tạo hình ảnh
            image, info = generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                model_id=model_id,
                seed=None  # Dùng hạt giống ngẫu nhiên
            )

            # Lưu hình ảnh
            image_path = os.path.join(output_dir, f"scene_{i:03d}.png")
            image.save(image_path)

            # Thêm vào danh sách đường dẫn
            image_paths.append(image_path)

            print(f"Tạo hình ảnh {i+1}/{len(prompts)}: {image_path}")
        except Exception as e:
            print(f"Tạo hình ảnh {i+1}/{len(prompts)} thất bại: {e}")
            # Nếu tạo thất bại, tạo một hình ảnh trắng
            blank_image = Image.new('RGB', (width, height), color='white')
            image_path = os.path.join(output_dir, f"scene_{i:03d}.png")
            blank_image.save(image_path)
            image_paths.append(image_path)
    
    return image_paths

def cleanup_resources():
    """
    Dọn dẹp tài nguyên, giải phóng bộ nhớ GPU
    """
    global pipeline_cache

    # Xoá bộ nhớ đệm mô hình
    for model_id, pipeline in pipeline_cache.items():
        del pipeline

    # Xoá từ điển bộ nhớ đệm
    pipeline_cache = {}

    # Dọn dẹp bộ nhớ đệm CUDA
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
