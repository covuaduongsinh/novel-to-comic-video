# Trình tạo video truyện tranh từ tiểu thuyết

Một ứng dụng web chuyển văn bản tiểu thuyết thành video truyện tranh, hỗ trợ nhiều phong cách truyện tranh, lồng tiếng AI và nhạc nền.

## Tính năng nổi bật

- **Văn bản thành truyện tranh**: Nhập văn bản tiểu thuyết, tự động chuyển thành hình ảnh phong cách truyện tranh, hỗ trợ chọn nhiều phong cách
- **Tạo video truyện tranh**: Ghép các hình ảnh truyện tranh đã tạo thành video, thêm hiệu ứng chuyển cảnh mượt mà, nâng cao trải nghiệm xem
- **Lồng tiếng thông minh**: Thêm lồng tiếng AI cho video, hỗ trợ chọn nhiều giọng nói, tăng cường trải nghiệm nghe nhìn
- **Nhạc nền**: Tùy chọn thêm nhạc nền, nâng cao chất lượng video
- **Nhiều phong cách**: Hỗ trợ phong cách truyện tranh mặc định, phong cách anime, phong cách tả thực, phong cách màu nước và phong cách ký hoạ

## Công nghệ sử dụng

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Tạo hình ảnh**: Stable Diffusion
- **Tổng hợp giọng nói**: Vbee TTS
- **Xử lý video**: MoviePy

## Cài đặt và sử dụng

1. Sao chép kho mã
```bash
git clone https://github.com/shen158598/novel-to-comic-video.git
cd novel-to-comic-video
```

2. Chạy ứng dụng
```bash
# Windows
run.bat

# Linux/Mac
bash run.sh
```

3. Mở trình duyệt và truy cập http://localhost:5000

## Cấu hình

Trước khi sử dụng, vui lòng đảm bảo cấu hình các nội dung sau:

1. Tạo tệp `.env` (tham khảo `.env.example`)
2. Cấu hình khoá API (Vbee TTS, Hugging Face, v.v.)
3. Tải tệp nhạc nền và đặt vào `static/audio/background.mp3`

## Giấy phép

MIT
