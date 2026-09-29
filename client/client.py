import sys
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import socket
import threading

from config import HOST, PORT, BUFFER_SIZE
from common.protocol import (
    MSG_JOIN, MSG_MSG, MSG_PRIVATE, MSG_QUIT,
    MSG_WELCOME, MSG_SYSTEM, MSG_ERROR, MSG_ONLINE_LIST,
    encode_message, decode_messages
)


class ChatClient:

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.client_socket = None
        self.username = None
        self.running = False
        self.online_users = []

    def connect(self):
        try:
            self.client_socket = socket.socket(
                socket.AF_INET,       # IPv4
                socket.SOCK_STREAM    # TCP
            )

            print(f"[CLIENT] Đang kết nối tới {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            print(f"[CLIENT] Đã kết nối thành công!")

            self.username = input("Nhập tên của bạn: ").strip()

            # Kiểm tra username không rỗng
            if not self.username:
                self.username = "Anonymous"

            join_msg = encode_message(MSG_JOIN, {
                "username": self.username
            })
            # sendall() đảm bảo gửi hết toàn bộ bytes
            self.client_socket.sendall(join_msg)

            raw_data = self.client_socket.recv(BUFFER_SIZE)

            if not raw_data:
                print("[CLIENT] Server đã đóng kết nối.")
                return

            messages = decode_messages(raw_data)
            for msg in messages:
                if msg['type'] == MSG_WELCOME:
                    print(f"\n✅ {msg['data']['message']}")
                elif msg['type'] == MSG_ERROR:
                    print(f"\n❌ Lỗi: {msg['data']['message']}")
                    return

            self.running = True
            print()
            print("=" * 55)
            print("  🎉 BẠN ĐÃ THAM GIA PHÒNG CHAT!")
            print("  - Gõ tin nhắn và nhấn Enter để gửi tới TẤT CẢ")
            print("  - Chat riêng: /w <tên> <nội dung> (hoặc /pm)")
            print("  - Xem danh sách online: /list")
            print("  - Trợ giúp: /help | Thoát: quit")
            print("=" * 55)
            print()

            recv_thread = threading.Thread(
                target=self._receive_messages,
                daemon=True
            )
            recv_thread.start()

            self._send_messages()

        except ConnectionRefusedError:
            print(f"\n[LỖI] Không thể kết nối tới Server {self.host}:{self.port}")
            print("       Hãy chắc chắn Server đang chạy!")

        except ConnectionResetError:
            print("\n[LỖI] Server đã ngắt kết nối đột ngột.")

        except Exception as e:
            print(f"\n[LỖI] {e}")

        finally:
            self.disconnect()

    def _receive_messages(self):
        while self.running:
            try:
                # recv() BLOCK ở đây cho đến khi có dữ liệu từ Server
                raw_data = self.client_socket.recv(BUFFER_SIZE)

                # bytes rỗng = Server đã đóng kết nối
                if not raw_data:
                    print("\n[CLIENT] Server đã ngắt kết nối.")
                    self.running = False
                    break

                # Phân tích và hiển thị tin nhắn
                messages = decode_messages(raw_data)

                for msg in messages:
                    msg_type = msg['type']

                    if msg_type == MSG_MSG:
                        # Tin nhắn chat chung 
                        sender = msg['data'].get('username', '???')
                        content = msg['data'].get('content', '')
                        timestamp = msg['data'].get('timestamp', '')
                        print(f"  [{timestamp}] {sender}: {content}")

                    elif msg_type == MSG_PRIVATE:
                        # Tin nhắn chat riêng 
                        from_user = msg['data'].get('from', '???')
                        to_user = msg['data'].get('to', '???')
                        content = msg['data'].get('content', '')
                        timestamp = msg['data'].get('timestamp', '')
                        is_sender = msg['data'].get('is_sender', False)

                        if is_sender:
                            print(f"  [{timestamp}] 🔒 [Gửi riêng tới {to_user}]: {content}")
                        else:
                            print(f"  [{timestamp}] 🔒 [Nhận riêng từ {from_user}]: {content}")

                    elif msg_type == MSG_ONLINE_LIST:
                        # ── Cập nhật danh sách online ──
                        self.online_users = msg['data'].get('users', [])
                        print(f"  👥 [Đang online ({len(self.online_users)})]: {', '.join(self.online_users)}")

                    elif msg_type == MSG_SYSTEM:
                        # ── Thông báo hệ thống ──
                        print(f"  📢 {msg['data']['message']}")

                    elif msg_type == MSG_ERROR:
                        # ── Thông báo lỗi ──
                        print(f"  ❌ Lỗi: {msg['data']['message']}")

            except ConnectionResetError:
                print("\n[CLIENT] Mất kết nối với Server.")
                self.running = False
                break

            except ConnectionAbortedError:
                break

            except OSError:
                break

    def _send_messages(self):
        while self.running:
            try:
                content = input()
                if not self.running:
                    break

                if content.lower().strip() == 'quit':
                    # Gửi QUIT cho Server biết Client muốn thoát
                    quit_msg = encode_message(MSG_QUIT, {})
                    try:
                        self.client_socket.sendall(quit_msg)
                    except OSError:
                        pass
                    print("[CLIENT] Đang ngắt kết nối...")
                    self.running = False
                    break

                # ── Bỏ qua tin nhắn rỗng ──
                trimmed = content.strip()
                if not trimmed:
                    continue

                # ── Lệnh xem trợ giúp ──
                if trimmed.lower() == '/help':
                    print("  ╭── HƯỚNG DẪN LỆNH CHAT ────────────")
                    print("  │ <tin nhắn>              : Gửi tới cả phòng")
                    print("  │ /w <tên> <nội dung>     : Chat riêng tư (Whisper/PM)")
                    print("  │ /list                   : Xem ai đang online")
                    print("  │ /help                   : Xem menu trợ giúp này")
                    print("  │ quit                    : Rời phòng chat")
                    print("  ╰───────────────────────────────────")
                    continue

                # Lệnh xem danh sách online
                if trimmed.lower() == '/list':
                    if self.online_users:
                        print(f"  👥 Thành viên online ({len(self.online_users)}): {', '.join(self.online_users)}")
                    else:
                        print("  👥 Chưa có dữ liệu danh sách online.")
                    continue

                # Lệnh chat riêng 
                if trimmed.startswith('/w ') or trimmed.startswith('/pm '):
                    parts = trimmed.split(' ', 2)
                    if len(parts) >= 3:
                        target_user = parts[1].strip()
                        pm_content = parts[2].strip()
                        if target_user and pm_content:
                            private_msg = encode_message(MSG_PRIVATE, {
                                "to": target_user,
                                "content": pm_content
                            })
                            self.client_socket.sendall(private_msg)
                            continue
                    print("  ⚠️ Sai cú pháp! Sử dụng: /w <tên_người_nhận> <nội dung>")
                    continue

                chat_msg = encode_message(MSG_MSG, {
                    "content": trimmed
                })
                self.client_socket.sendall(chat_msg)

            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

            except (BrokenPipeError, ConnectionResetError, OSError):
                print("\n[CLIENT] Mất kết nối với Server.")
                self.running = False
                break

    def disconnect(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except OSError:
                pass
        print("[CLIENT] Đã ngắt kết nối.")
