@echo off
echo Dang khoi dong ung dung chuyen tieu thuyet thanh truyen tranh...

:: Kiem tra Python da cai dat chua
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python chua duoc cai dat, vui long cai Python 3.8-3.10 truoc
    pause
    exit /b
)

:: Kiem tra da cai dat phu thuoc chua
if not exist venv (
    echo Chay lan dau, dang tao moi truong ao...
    python -m venv venv
    call venv\Scripts\activate
    echo Dang cai dat phu thuoc...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: Khoi dong ung dung
echo Khoi dong ung dung...
python app.py

pause