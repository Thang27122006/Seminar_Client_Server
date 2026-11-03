#!/usr/bin/env python3
"""
Trình khởi chạy Máy Chủ Trung Tâm (Central Seminar Server)
Seminar Lập Trình Mạng: Hệ Thống Hội Nghị & Chat Client - Server
"""

import os
import sys
import socket
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Tự động chuyển đổi sang môi trường ảo .venv nếu chưa kích hoạt
VENV_PYTHON = os.path.join(BASE_DIR, '.venv', 'bin', 'python3')
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    try:
        import aiohttp
    except ImportError:
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import config
from server.hub_server import start_dual_server, HOST, WEB_PORT, TCP_PORT


def get_local_ip():
    """Lấy địa chỉ IP mạng nội bộ (LAN) của máy."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def print_banner(local_ip):
    banner = f"""
╔══════════════════════════════════════════════════════════════════════╗
║    🚀 SEMINAR LẬP TRÌNH MẠNG - MÁY CHỦ TRUNG TÂM CLIENT - SERVER     ║
╚══════════════════════════════════════════════════════════════════════╝

  🖥️ GIAO DIỆN QUẢN TRỊ PHIÊN HỌP (SERVER GUI CONTROLLER):
     ► Khởi chạy đồ họa Server GUI: python3 run_server_gui.py

  💻 CHƯƠNG TRÌNH KHÁCH (DESKTOP CLIENT):
     ► Khởi chạy ứng dụng Meet:     python3 run_app.py
     ► Khởi chạy giao diện GUI:     python3 run_gui.py

  🔌 CỔNG DỊCH VỤ MÁY CHỦ:
     ► Cổng điều phối đa phương tiện: 127.0.0.1:{WEB_PORT}
     ► Cổng kết nối TCP Socket:       127.0.0.1:{TCP_PORT}
     ► Kết nối từ máy khác trong LAN: {local_ip}:{WEB_PORT}

  ✨ TÍNH NĂNG NỔI BẬT:
     ✓ Quản lý phiên Client ID duy nhất, xác thực PostgreSQL (pgAdmin4) & SQLite
     ✓ Đa phòng họp tự động đồng bộ thời gian thực
     ✓ Hỗ trợ cuộc gọi video, chia sẻ màn hình, chuông âm báo Google Meet
     ✓ Gửi file tài liệu, gửi hình ảnh trực tiếp trong cuộc gọi
     ✓ Nhắn tin riêng 1-1 bảo mật giữa các thành viên
     ✓ Dừng máy chủ: Nhấn [Ctrl + C]

──────────────────────────────────────────────────────────────────────
"""
    print(banner)


def main():
    if '--gui' in sys.argv or '-g' in sys.argv:
        from server.gui import ServerGUI
        app = ServerGUI()
        app.run()
        return

    if '--tcp-only' in sys.argv:
        from server.server import ChatServer
        server = ChatServer()
        server.start()
        return

    local_ip = get_local_ip()
    print_banner(local_ip)

    try:
        asyncio.run(start_dual_server(host=HOST, web_port=WEB_PORT, tcp_port=TCP_PORT))
    except KeyboardInterrupt:
        print("\n[SERVER] Đã ngắt máy chủ an toàn. Hẹn gặp lại!")


if __name__ == '__main__':
    main()
