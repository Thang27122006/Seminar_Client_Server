#!/usr/bin/env python3
"""
Trình khởi chạy Ứng dụng Desktop (Desktop Application Launcher)
Seminar Lập Trình Mạng: Hội Nghị Trực Tuyến & Chat Client-Server

Cách dùng:
    python3 run_app.py               # Mở trang chủ Google Meet (Tạo cuộc họp mới / Tham gia)
    python3 run_app.py <mã_phòng>    # Vào trực tiếp mã phòng bất kỳ (ví dụ: seminar-network-lab)
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from client.desktop_app import main

if __name__ == '__main__':
    main()
