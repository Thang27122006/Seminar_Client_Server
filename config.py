# Địa chỉ IP của Server
# '127.0.0.1' (localhost): Server chạy trên chính máy này
# Đổi thành '0.0.0.0' nếu muốn máy khác trong mạng LAN kết nối được
HOST = '192.168.1.7'
# Port lắng nghe của Server
# Chọn port trong khoảng 1024-65535 để tránh xung đột với hệ thống
PORT = 9000
# =====================================================================
# CẤU HÌNH DỮ LIỆU
# =====================================================================
# Kích thước buffer khi nhận dữ liệu (đơn vị: bytes)
# 4096 bytes = 4KB, đủ lớn cho tin nhắn chat thông thường
# Nếu tin nhắn dài hơn 4KB, cần recv() nhiều lần
BUFFER_SIZE = 4096
# Bảng mã ký tự khi chuyển đổi string <-> bytes
# UTF-8 hỗ trợ tiếng Việt và hầu hết ngôn ngữ trên thế giới
ENCODING = 'utf-8'