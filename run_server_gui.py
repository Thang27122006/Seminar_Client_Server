#!/usr/bin/env python3
"""
Trình khởi chạy Giao Diện Máy Chủ Điều Phối Phiên Họp (Server GUI Controller)
Seminar Lập Trình Mạng: Hệ Thống Hội Nghị Trực Tuyến & Chat Client - Server

Quản lý trực quan:
- Danh sách các phòng họp (Tạo phòng, Khóa phòng, Mute All, Giải tán)
- Thành viên tham gia theo từng phòng (Desktop App & TCP Socket)
- Kích, Tắt tiếng (Mute/Unmute), Nhắn tin riêng
- Phát thông báo khẩn toàn máy chủ hoặc theo từng phòng
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Tự động chuyển đổi sang môi trường ảo .venv nếu chưa kích hoạt
VENV_PYTHON = os.path.join(BASE_DIR, '.venv', 'bin', 'python3')
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    try:
        import aiohttp
    except ImportError:
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

from server.gui import ServerGUI


def main():
    app = ServerGUI()
    app.run()


if __name__ == '__main__':
    main()
