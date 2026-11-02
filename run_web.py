#!/usr/bin/env python3
"""
Trình khởi chạy Nền Tảng Web (Web Platform Launcher)
Seminar Lập Trình Mạng: Client - Server Chat Application
"""

import os
import sys
import socket
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Tự động chuyển đổi sang môi trường ảo .venv nếu chưa kích hoạt
VENV_PYTHON = os.path.join(BASE_DIR, '.venv', 'bin', 'python3')
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    try:
        import aiohttp
    except ImportError:
        # Re-exec với Python trong .venv
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

# 2. Kiểm tra thư viện aiohttp
try:
    import aiohttp
except ImportError:
    print("=" * 65)
    print("❌ LỖI: Chưa cài đặt thư viện 'aiohttp'!")
    print("Vui lòng kích hoạt virtualenv hoặc chạy lệnh sau trong terminal:")
    print("    pip install aiohttp")
    print("hoặc:")
    print("    .venv/bin/pip install aiohttp")
    print("=" * 65)
    sys.exit(1)

# Import cấu hình và máy chủ web
import config
from server.web_server import start_dual_server, HOST, WEB_PORT, TCP_PORT
import asyncio

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
╔══════════════════════════════════════════════════════════════════════════╗
║    🚀 SEMINAR LẬP TRÌNH MẠNG - HỘI NGHỊ TRUYỀN HÌNH ZOOM & MEET WEB      ║
╚══════════════════════════════════════════════════════════════════════════╝

  🌐 TRANG CHỦ HỘI NGHỊ (GOOGLE MEET & ZOOM HOME LOBBY):
     ► Trên máy này:         http://localhost:{WEB_PORT}
     ► Máy khác trong LAN:   http://{local_ip}:{WEB_PORT}
     (Hỗ trợ Đăng ký/Đăng nhập, Tạo cuộc họp mới, Nhập mã phòng tham gia)

  📹 PHÒNG HỌP TRỰC TUYẾN (IN-MEETING VIDEO & CHAT ROOM):
     ► Đường dẫn trực tiếp:  http://localhost:{WEB_PORT}/room?code=seminar-network-lab

  👑 TRANG QUẢN TRỊ RIÊNG BIỆT (HOST STUDIO - MEET / ZOOM STYLE):
     ► Quản trị viên (Host): http://localhost:{WEB_PORT}/admin

  🔌 MÁY CHỦ TCP SOCKET TRUYỀN THỐNG (Port {TCP_PORT}):
     ► Hỗ trợ kết nối song song các Desktop Client cũ:
       - python3 run_gui.py       (Giao diện Tkinter Client)
       - python3 run_client.py    (CLI Client)

  ✨ ĐẶC TÍNH NỔI BẬT:
     ✓ Xác thực người dùng (Auth Register/Login), lưu trữ tài khoản SQLite
     ✓ Quản lý đa phòng họp (Multi-Room) sinh mã ngẫu nhiên dạng abc-defg-hij
     ✓ Web Client & Desktop Client chat chung trong cùng 1 phòng theo thời gian thực
     ✓ Host Control Studio: Khóa phòng, Mute All, Kick, Gửi thông báo khẩn
     ✓ Phím tắt dừng máy chủ: Nhấn [Ctrl + C]

──────────────────────────────────────────────────────────────────────────
"""
    print(banner)

def main():
    local_ip = get_local_ip()
    print_banner(local_ip)

    try:
        asyncio.run(start_dual_server(host=HOST, web_port=WEB_PORT, tcp_port=TCP_PORT))
    except KeyboardInterrupt:
        print("\n[SERVER] Đã ngắt máy chủ an toàn. Hẹn gặp lại!")

if __name__ == '__main__':
    main()
