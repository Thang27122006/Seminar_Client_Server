# Địa chỉ IP của Server
# '127.0.0.1' (localhost): Server chạy trên chính máy này
# '0.0.0.0': Cho phép kết nối từ cả máy này lẫn các máy khác trong mạng LAN
HOST = '127.0.0.1'

# Port lắng nghe của Server TCP Socket (Dành cho Client Python Desktop)
PORT = 9000

# Port Dịch Vụ Hub Desktop (HTTP & WebSocket nội bộ điều phối giao diện Desktop)
WEB_PORT = 8080
HUB_PORT = WEB_PORT

# =====================================================================
# CẤU HÌNH DỮ LIỆU
# =====================================================================
# Kích thước buffer khi nhận dữ liệu (đơn vị: bytes)
BUFFER_SIZE = 4096

# Bảng mã ký tự khi chuyển đổi string <-> bytes
ENCODING = 'utf-8'

# =====================================================================
# CẤU HÌNH CƠ SỞ DỮ LIỆU (POSTGRESQL / PGADMIN4)
# =====================================================================
import os

# DB_ENGINE: 'postgresql' (kết nối pgAdmin4) hoặc 'sqlite' (dự phòng nội bộ)
DB_ENGINE = os.environ.get('DB_ENGINE', 'postgresql')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('DB_PORT', 5432))
DB_NAME = os.environ.get('DB_NAME', 'seminar_meet_db')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '123')