# 🌐 HƯỚNG DẪN SỬ DỤNG NỀN TẢNG GOOGLE MEET & SEMINAR LẬP TRÌNH MẠNG
> **Đồ án:** Nền Tảng Hội Nghị Trực Tuyến 100% Google Meet Đa Giao Thức (WebSocket & TCP Socket Bridge) kèm Bảng Điều Khiển Giám Sát Mạng Thời Gian Thực.

---

## 🎯 1. Tổng Quan Kiến Trúc Nâng Cấp

Dự án đã được chuyển đổi và nâng cấp toàn diện sang nền tảng **100% Google Meet Web Experience** với trải nghiệm người dùng chân thực, mượt mà và đạt tiêu chuẩn sản phẩm cao cấp:

```
                        ┌───────────────────────────────────────────────┐
                        │          TRÌNH DUYỆT WEB (Mọi thiết bị)        │
                        │       Google Meet UI • WebRTC • WebSocket     │
                        └───────────────────────┬───────────────────────┘
                                                │ (WebSocket / HTTP: 8080)
                                                ▼
┌───────────────────────┐       ┌───────────────────────────────────────────────┐
│  DESKTOP CLIENT (GUI) │       │            CENTRAL DUAL-HUB SERVER            │
│  Python Tkinter / CLI │◄─────►│    aiohttp (Web + WS) + asyncio (TCP 9000)    │
└───────────────────────┘ (TCP) └───────────────────────────────────────────────┘
```

### ✨ Các Điểm Đột Phá Chuẩn Google Meet:
1. **Trang Chủ Hội Nghị (Google Meet Home Lobby - `/`):**
   - Logo camera 4 màu đặc trưng của Google Meet.
   - Nút **[➕ Cuộc họp mới]** với menu xổ xuống:
     - 🔗 *Tạo một cuộc họp để sử dụng sau* (Sinh mã ngẫu nhiên dạng `abc-defg-hij`, kèm popup sao chép link).
     - ⚡ *Bắt đầu một cuộc họp tức thì* (Vào phòng ngay lập tức với quyền Host).
     - 👑 *Mở Host Control Studio* (Trung tâm quản trị cuộc họp nâng cao).
   - Ô nhập **[⌨️ Nhập một mã hoặc đường liên kết]** + Nút **[Tham gia]**.
   - Băng chuyền trình chiếu 3 slide minh họa các tính năng của Google Meet.
   - Thẻ danh sách các cuộc họp đang diễn ra kèm số lượng người online cập nhật tự động.

2. **Sảnh Chờ & Kiểm Tra Thiết Bị (Signature Green Room Preview - `/room?code=...`):**
   - Khung xem trước 16:9 với webcam trực tiếp qua `navigator.mediaDevices.getUserMedia`.
   - Vòng tròn Avatar với chữ cái đầu khi tắt máy ảnh.
   - Cặp nút tròn bật/tắt nhanh Micrô & Máy ảnh trên sảnh chờ kèm phím tắt `Ctrl+D` và `Ctrl+E`.
   - Cột thông tin: *"Sẵn sàng tham gia?"*, số người đang có trong phòng, ô nhập tên hiển thị.
   - Hai nút hành động: **[Tham gia ngay]** và **[Trình bày]** (chia sẻ màn hình trực tiếp).

3. **Giao Diện Trong Cuộc Gọi (In-Call Google Meet Stage):**
   - Tone màu nền tối chuẩn `#202124` của Google Meet.
   - **Lưới ô người tham gia thích ứng động (Dynamic Video Tiles Grid):**
     - Tự động chia bố cục 1, 2, 3, 4, 5-9 người trên cùng màn hình.
     - Viền phát sáng xanh dương chuyển động (Speaking indicator halo) theo giọng nói thực tế thông qua Web Audio API `AnalyserNode`.
     - Huy hiệu giơ tay phát biểu ✋ nổi bật ở góc trên bên trái của ô.
     - Thẻ tên ở góc dưới bên trái hiển thị tên, trạng thái mic và nhãn nền tảng (`🌐 Web` hoặc `💻 TCP`).
   - **Trình chiếu màn hình (Screen Sharing Mode):**
     - Tích hợp `navigator.mediaDevices.getDisplayMedia` chuẩn trình duyệt.
     - Sân khấu trình bày chiếm tiêu điểm với banner xanh "Bạn đang trình bày màn hình cho mọi người".
   - **Thả biểu tượng cảm xúc nổi (Floating Reactions):**
     - Menu biểu cảm 💖, 👍, 🎉, 👏, 😂, 😮.
     - Bong bóng emoji bay lên với hiệu ứng chuyển động chân thực.
   - **Hệ thống âm thanh Web Audio API thuần:**
     - Chuông giơ tay chuẩn Google Meet (Triple-tone warm chime: C5 -> E5 -> G5).
     - Âm thanh người tham gia / rời phòng và âm thanh tin nhắn trò chuyện.

4. **Thanh Điều Khiển Đáy Chuẩn Google Meet (Bottom Floating Pill Bar):**
   - **Cụm trái:** Đồng hồ thời gian thực (`22:30`) | Mã cuộc họp (`abc-defg-hij`) kèm nút sao chép link.
   - **Cụm giữa:** Các nút tròn thao tác: Micrô, Máy ảnh, Phụ đề (CC), Biểu tượng cảm xúc, Chia sẻ màn hình, Giơ tay phát biểu, Tùy chọn khác (Toàn màn hình), và Nút Đỏ Rời Cuộc Gọi hình viên thuốc rộng.
   - **Cụm phải:** Các nút mở ngăn kéo: Chi tiết cuộc họp (ℹ️), Mọi người (👥 với huy hiệu đếm số lượng), Tin nhắn trò chuyện (💬 với huy hiệu tin nhắn chưa đọc), và Bộ điều khiển của người tổ chức (🔒).

5. **Ngăn Kéo Bên Phải (Right Slide-in Drawer):**
   - **Mọi người (People):** Danh sách thành viên trong cuộc gọi, trạng thái mic, nhãn Chủ trì, nút *Tắt tiếng tất cả* (Mute all).
   - **Tin nhắn trong cuộc gọi (In-Call Chat):** Dòng thông báo bản quyền chuẩn Google Meet, bong bóng chat kèm thời gian, hỗ trợ tin nhắn công khai và tin nhắn riêng tư (Whisper).
   - **Bộ điều khiển của người tổ chức (Host Controls):** Các công tắc bật/tắt quyền của người tham gia: *Chia sẻ màn hình*, *Gửi tin nhắn trò chuyện*, *Bật micrô*, *Bật máy ảnh*.
   - **Chi tiết cuộc họp (Info):** Hiển thị link cuộc họp kèm nút sao chép và thông báo toast.

6. **Cầu Nối Đa Giao Thức (Dual-Protocol Bridge):**
   - Web Client kết nối qua **WebSocket** (`ws://localhost:8080/ws`).
   - Desktop Client Python Tkinter (`run_gui.py`, `run_client.py`) kết nối qua **TCP Socket** (`localhost:9000`).
   - Cả 2 nền tảng cùng tham gia vào phòng họp `seminar-network-lab` hoặc bất kỳ phòng họp nào, đồng bộ danh sách online và trò chuyện hai chiều mượt mà!

---

## 🚀 2. Hướng Dẫn Khởi Chạy

### Bước 1: Khởi động Máy Chủ
Chạy lệnh duy nhất tại thư mục gốc của dự án:
```bash
python3 run_web.py
```
*Script sẽ tự động nhận diện virtualenv `.venv`, in banner đẹp mắt ra terminal và lắng nghe đồng thời trên cả Port 8080 (Web) và Port 9000 (TCP).*

### Bước 2: Truy Cập Trình Duyệt Web
Mở trình duyệt (Chrome, Edge, Firefox, Cốc Cốc, Safari):
- **Trang Chủ Google Meet Lobby:** [http://localhost:8080](http://localhost:8080)
- **Vào Thẳng Phòng Họp Mặc Định:** [http://localhost:8080/room?code=seminar-network-lab](http://localhost:8080/room?code=seminar-network-lab)
- **Trang Quản Trị Host Studio:** [http://localhost:8080/admin](http://localhost:8080/admin)
- **Truy cập từ điện thoại / laptop khác trong cùng mạng Wi-Fi/LAN:** `http://<IP_LAN_CỦA_MÁY>:8080`

### Bước 3: Tài Khoản Demo Có Sẵn
Hệ thống tích hợp sẵn cơ sở dữ liệu SQLite (`data/netsphere.db`) với mật khẩu mã hóa SHA-256 + Salt:
- **Quản trị viên (Admin):** Username `admin` | Password `admin123`
- **Giảng viên hướng dẫn (Host):** Username `giangvien` | Password `123456`
- **Sinh viên báo cáo:** Username `sinhvien1` | Password `123456`
*(Người dùng cũng có thể tự tạo tài khoản mới bằng nút **Đăng ký** hoặc tham gia với tư cách **Khách**)*

---

## 💻 3. Biểu Diễn Seminar Đa Giao Thức (Web + Desktop TCP)

Để tạo điểm nhấn xuất sắc trong bài báo cáo Seminar:
1. **Terminal 1:** Khởi chạy Web Server:
   ```bash
   python3 run_web.py
   ```
2. **Trình duyệt Web:** Truy cập `http://localhost:8080`, đăng nhập tài khoản `sinhvien1` và bấm **Cuộc họp mới -> Bắt đầu tức thì**.
3. **Terminal 2:** Khởi chạy Desktop Client Tkinter truyền thống:
   ```bash
   python3 run_gui.py
   ```
   *(Nhập tên ví dụ: `SinhVien_Desktop`, bấm Kết nối tới localhost:9000)*
4. 💬 **Kết quả biểu diễn:**
   - Trên Web Google Meet, ô video tile của `SinhVien_Desktop` lập tức xuất hiện kèm huy hiệu `💻 TCP`.
   - Tin nhắn gửi từ Desktop Client hiển thị ngay trong drawer trò chuyện của Google Meet.
   - Tin nhắn gửi từ Google Meet phản hồi lập tức về cửa sổ Tkinter Desktop!

---

## 📁 4. Cấu Trúc Mã Nguồn Sau Nâng Cấp

```text
Seminar_Client_Server/
├── web/                           # Giao diện Web 100% Google Meet
│   ├── home.html                  # Trang chủ Google Meet Lobby (Nút tạo phòng, nhập mã, carousel)
│   ├── room.html                  # Giao diện phòng họp (Sảnh chờ Green Room & Sân khấu In-Call)
│   ├── admin.html                 # Host Studio trung tâm điều khiển
│   ├── css/
│   │   ├── home.css               # Phong cách thiết kế Google Meet Home
│   │   ├── room.css               # Phong cách thiết kế In-Call & Green Room chuẩn #202124
│   │   ├── admin.css              # Phong cách thiết kế Host Studio
│   │   └── style.css              # Hệ thống CSS dùng chung
│   └── js/
│       ├── auth.js                # Quản lý phiên đăng nhập, JWT token, SQLite API
│       ├── home.js                # Logic trang chủ (Đồng hồ, carousel, popup tạo phòng, active rooms)
│       ├── meet_room.js           # Lõi Google Meet (Green room, WebRTC, grid, giơ tay, reactions, chat)
│       ├── sound_fx.js            # Bộ tổng hợp âm thanh chuông Meet Web Audio API
│       └── host_meeting.js        # Logic điều khiển quản trị Host
├── server/
│   ├── web_server.py              # Server cầu nối đa giao thức (HTTP + WebSocket 8080 & TCP Socket 9000)
│   ├── auth.py                    # Xác thực tài khoản SQLite & tạo session tokens
│   ├── rooms.py                   # Quản lý đa phòng họp trực tuyến (mã abc-defg-hij)
│   ├── server.py                  # Server TCP socket cũ
│   └── gui.py                     # Giao diện quản trị Server Tkinter cũ
├── client/
│   ├── client.py                  # Client CLI TCP socket
│   └── gui.py                     # Client GUI Tkinter
├── common/
│   └── protocol.py                # Định dạng gói tin giao thức mạng
├── config.py                      # Cấu hình IP, TCP Port (9000), Web Port (8080)
├── run_web.py                     # Trình khởi chạy Nền Tảng Web thông minh
└── README_WEB.md                  # Tài liệu hướng dẫn này
```

---

## ⌨️ 5. Phím Tắt Tiện Dụng Chuẩn Google Meet

| Phím tắt | Thao tác tương ứng |
| :--- | :--- |
| `Ctrl + D` | Bật / Tắt Micrô |
| `Ctrl + E` | Bật / Tắt Máy ảnh |
| `c` | Bật / Tắt Phụ đề trực tiếp (Captions) |
| `Ctrl + H` | Giơ tay phát biểu / Hạ tay xuống |
| `Enter` | Gửi tin nhắn trò chuyện |
