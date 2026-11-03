# 💻 ĐỒ ÁN SEMINAR LẬP TRÌNH MẠNG: HỆ THỐNG HỘI NGHỊ & CHAT CLIENT - SERVER
> **Ứng dụng:** Google Meet Desktop Edition — Mô hình Client - Server Đa Giao Thức (WebSocket & TCP Socket Bridge) kèm Giao Diện Quản Trị Server GUI Controller.

---

## 🎯 1. Tổng Quan Kiến Trúc Ứng Dụng Desktop

Hệ thống được thiết kế theo mô hình **Client - Server** hoàn chỉnh, đóng gói thành **Cửa Sổ Ứng Dụng Desktop (Desktop App Window)** độc lập, hoạt động không cần thanh điều hướng trình duyệt:

```text
┌─────────────────────────────────────────────────────────────┐
│             DESKTOP APPLICATION (Cửa Sổ Độc Lập)            │
│         Google Meet UI • Video Call • Screen Share          │
│            Gửi File / Ảnh • Chat Riêng 1-1 • Mic            │
└──────────────────────────────┬──────────────────────────────┘
                               │ (WebSocket / Local Service Port 8080)
                               ▼
┌──────────────────────────────┴──────────────────────────────┐
│                  MÁY CHỦ TRUNG TÂM (SERVER)                 │
│                 hub_server.py / run_server.py               │
│        - Điều phối Đa phương tiện & File (Port 8080)         │
│        - Quản lý TCP Socket Server đa luồng (Port 9000)     │
│        - Cơ sở dữ liệu SQLite & Quản lý Đa phòng họp        │
└──────────────────────────────┬──────────────────────────────┘
                               ▲ (TCP Socket Port 9000)
                               │
┌──────────────────────────────┴──────────────────────────────┐
│                 DESKTOP CLIENT TRUYỀN THỐNG                 │
│              Python Tkinter GUI / CLI Client                │
│         (run_gui.py --classic / run_client.py)              │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ 2. Các Tính Năng Chính Của Ứng Dụng

1. **Cửa Sổ Ứng Dụng Desktop Độc Lập (Desktop App Mode):**
   - Khởi chạy trực tiếp từ terminal hoặc file script `run_app.py` / `run_app.sh`.
   - Cửa sổ phần mềm riêng biệt, giao diện dark mode sang trọng chuẩn Google Meet (`#202124`).

2. **Sảnh Chờ & Thiết Bị (Green Room Preview):**
   - Xem trước webcam, kiểm tra micrô trước khi tham gia cuộc họp.
   - Phím tắt bật/tắt nhanh: `Ctrl + D` (Mic), `Ctrl + E` (Camera).
   - Tự động gán Avatar tròn theo chữ cái đầu tên người dùng.

3. **Giao Diện Cuộc Gọi (In-Meeting Video & Stage):**
   - Bố cục lưới ô (Video Tiles Grid) thích ứng động theo số lượng người tham gia.
   - **Chia sẻ màn hình thời gian thực:** Trình chiếu màn hình cho toàn bộ thành viên trong phòng.
   - **Gửi File & Gửi Hình Ảnh:** Đính kèm tài liệu học tập, ảnh trực tiếp trong khung trò chuyện, hỗ trợ xem trước và tải về.
   - **Nhắn Tin Riêng 1-1 (Private Message):** Nhấn vào bất kỳ người tham gia nào trong danh sách để mở chế độ chat riêng tư kèm gửi file/ảnh bí mật.
   - **Giơ tay phát biểu (Raise Hand):** Kèm chuông âm báo Google Meet 3 tone ấm áp.
   - **Biểu tượng cảm xúc nổi (Reactions):** Thả tim, vỗ tay, like, cười bay lượn sinh động.

4. **Trung Tâm Quản Trị (Host Control Studio):**
   - Quản lý phòng họp: Khóa phòng, Tắt tiếng tất cả (Mute All).
   - Phân quyền người tham gia: Bật/tắt quyền chia sẻ màn hình, bật mic, bật cam.
   - Giám sát lưu lượng mạng, số lượng gói tin truyền nhận theo thời gian thực.

5. **Đồng Bộ Hai Chiều Với TCP Socket:**
   - Hỗ trợ kết nối song song các Desktop Client viết bằng Python Tkinter truyền thống qua cổng TCP 9000.
   - Tin nhắn và danh sách online được đồng bộ tức thì giữa tất cả các ứng dụng.

---

## 🚀 3. Hướng Dẫn Cài Đặt & Sử Dụng

### Yêu Cầu Môi Trường:
- Python 3.8 trở lên.
- Đã cài đặt thư viện phụ thuộc (`aiohttp`):
  ```bash
  pip install aiohttp
  ```

---

### Bước 1: Khởi Động Máy Chủ (Server)
Bạn có thể khởi động Máy chủ bằng **Giao diện đồ họa (GUI)** hoặc **Dòng lệnh (CLI)**:

* **Cách 1 (Khuyên dùng - Có giao diện quản lý phiên họp trực quan):**
  ```bash
  python3 run_server_gui.py
  ```
  *(Mở cửa sổ đồ họa Desktop quản lý đa phòng họp, thành viên, khóa phòng, mute all, phát thông báo khẩn và live log)*

* **Cách 2 (Chạy ngầm dòng lệnh trong terminal):**
  ```bash
  python3 run_server.py
  ```
> *Máy chủ sẽ tự động lắng nghe cổng điều phối 8080 và cổng TCP Socket 9000.*

---

### Bước 2: Khởi Chạy Ứng Dụng Desktop (Desktop Client)
Mở một Terminal khác và chạy:
```bash
python3 run_app.py
```
> *Ứng dụng sẽ mở ra cửa sổ Desktop chuyên nghiệp chuẩn Google Meet.*

**Các tuỳ chọn khởi chạy nhanh:**
```bash
python3 run_app.py               # Mở trang chủ Google Meet (Tạo cuộc họp mới / Tham gia)
python3 run_app.py <mã_phòng>    # Vào trực tiếp mã phòng cụ thể (ví dụ: seminar-network-lab)
```

---

### Bước 3: Biểu Diễn Kết Nối Đa Client (Tùy Chọn)
Để biểu diễn khả năng tương thích đa giao thức của đồ án:
1. Mở Desktop App chính:
   ```bash
   python3 run_app.py
   ```
2. Mở thêm một Desktop Client giao diện Tkinter truyền thống:
   ```bash
   python3 run_gui.py --classic
   ```
3. Nhập tên và tham gia chat — cả hai ứng dụng Desktop sẽ thấy nhau và trò chuyện thời gian thực!

---

## 📁 4. Cấu Trúc Mã Nguồn

```text
Seminar_Client_Server/
├── run_server.py                  # Trình khởi chạy Máy Chủ Trung Tâm (Server)
├── run_app.py                     # Trình khởi chạy Ứng Dụng Desktop (Client)
├── run_app.sh                     # Script khởi chạy nhanh trên Linux/macOS
├── run_gui.py                     # Trình khởi chạy Client GUI (hỗ trợ --classic Tkinter)
├── run_client.py                  # Trình khởi chạy Client CLI truyền thống
├── config.py                      # Cấu hình IP, Cổng Socket TCP (9000) & Hub (8080)
│
├── client/
│   ├── desktop_app.py             # Bộ điều khiển Cửa Sổ Ứng Dụng Desktop độc lập
│   ├── client.py                  # Client Socket TCP thuần (CLI)
│   └── gui.py                     # Client Giao diện Tkinter truyền thống
│
├── server/
│   ├── hub_server.py              # Lõi Máy Chủ điều phối đa giao thức & đa phương tiện
│   ├── auth.py                    # Quản lý tài khoản và phiên làm việc (SQLite)
│   ├── rooms.py                   # Quản lý đa phòng họp (mã phòng dạng abc-defg-hij)
│   ├── server.py                  # Server TCP Socket thuần
│   └── gui.py                     # Giao diện giám sát Server Tkinter
│
├── common/
│   └── protocol.py                # Định dạng cấu trúc gói tin giao thức mạng
│
├── ui/                            # Tài nguyên giao diện ứng dụng Desktop
│   ├── home.html                  # Giao diện Trang chủ (Tạo cuộc họp / Nhập mã)
│   ├── room.html                  # Giao diện Phòng họp Meet (Video, Chat, File, Screen)
│   ├── css/                       # Hệ thống stylesheet giao diện
│   └── js/                        # Bộ điều khiển logic giao diện & kết nối mạng
│
└── data/                          # Cơ sở dữ liệu SQLite và thư mục lưu trữ file gửi
    └── uploads/                   # Thư mục lưu trữ các tệp tin / hình ảnh đính kèm
```

---

## ⌨️ 5. Phím Tắt Tiện Dụng Trong Cuộc Gọi

| Phím tắt | Chức năng |
| :--- | :--- |
| `Ctrl + D` | Bật / Tắt Micrô |
| `Ctrl + E` | Bật / Tắt Máy ảnh |
| `Ctrl + H` | Giơ tay phát biểu / Hạ tay xuống |
| `Enter` | Gửi tin nhắn trò chuyện |
