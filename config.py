# Địa chỉ IP của Server
# '127.0.0.1' (localhost): Server chạy trên chính máy này
# '0.0.0.0': Cho phép kết nối từ cả máy này lẫn các máy khác trong mạng LAN
HOST = '127.0.0.1'

# Port lắng nghe của Server TCP Socket (Dành cho Client Python Desktop)
PORT = 9000

# Port Web Server (HTTP & WebSocket - Dành cho trình duyệt Web)
WEB_PORT = 8080

# =====================================================================
# CẤU HÌNH DỮ LIỆU
# =====================================================================
# Kích thước buffer khi nhận dữ liệu (đơn vị: bytes)
BUFFER_SIZE = 4096

# Bảng mã ký tự khi chuyển đổi string <-> bytes
ENCODING = 'utf-8'