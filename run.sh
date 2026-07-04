#!/bin/bash
echo "Đang khởi động ứng dụng chuyển tiểu thuyết thành truyện tranh..."

# Kiểm tra Python đã cài đặt chưa
if ! command -v python3 &> /dev/null; then
    echo "Python chưa được cài đặt, vui lòng cài Python 3.8-3.10 trước"
    exit 1
fi

# Kiểm tra đã cài đặt phụ thuộc chưa
if [ ! -d "venv" ]; then
    echo "Chạy lần đầu, đang tạo môi trường ảo..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Đang cài đặt phụ thuộc..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Khởi động ứng dụng
echo "Khởi động ứng dụng..."
python app.py
