import sys
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import socket
import threading
from datetime import datetime

from config import HOST, PORT, BUFFER_SIZE
from common.protocol import (
    MSG_JOIN, MSG_MSG, MSG_PRIVATE, MSG_QUIT,
    MSG_WELCOME, MSG_SYSTEM, MSG_ERROR, MSG_ONLINE_LIST,
    encode_message, decode_messages
)


class ClientSession:
    """
    Quản lý thông tin chi tiết của một phiên kết nối Client,
    bao gồm ID duy nhất, socket, địa chỉ IP:Port, username và thống kê.
    """

    def __init__(self, client_id, client_socket, client_address):
        self.id = client_id
        self.socket = client_socket
        self.address = client_address
        self.ip = client_address[0] if client_address else "127.0.0.1"
        self.port = client_address[1] if client_address else 0
        self.username = None
        self.connected_at = datetime.now()
        self.fileno = client_socket.fileno() if hasattr(client_socket, 'fileno') else -1
        self.msg_count = 0
        self.status = "Chờ JOIN"
        self.is_active = True

    def to_dict(self):
        """Chuyển đổi thành từ điển phục vụ hiển thị trên Giao diện GUI."""
        return {
            "id": self.id,
            "username": self.username or "(Chờ JOIN)",
            "ip": self.ip,
            "port": self.port,
            "address": f"{self.ip}:{self.port}",
            "fileno": self.fileno,
            "connected_at": self.connected_at.strftime("%H:%M:%S"),
            "status": self.status,
            "msg_count": self.msg_count,
            "is_active": self.is_active
        }


class ChatServer:
    """
    TCP Chat Server hỗ trợ đa Client, gán và theo dõi Client ID duy nhất,
    cung cấp các hook sự kiện để tích hợp giao diện điều khiển GUI hoặc chạy CLI.
    """

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

        # Bộ đếm định danh Client ID duy nhất
        self.client_id_counter = 0
        self.total_connections = 0
        self.total_messages = 0

        # Mapping: client_socket -> ClientSession
        self.clients = {}
        self.clients_lock = threading.Lock()

        # Lịch sử các phiên đã ngắt kết nối (tùy chọn tra cứu)
        self.client_history = []

        # Hệ thống Callback phục vụ cập nhật Giao diện đồ họa (GUI)
        self.callbacks = {
            'on_log': [],
            'on_status': [],
            'on_client_connect': [],
            'on_client_join': [],
            'on_client_leave': [],
            'on_client_update': [],
            'on_message': []
        }

    # ─────────────────────────────────────────────────────────────────
    # QUẢN LÝ CALLBACK & NHẬT KÝ
    # ─────────────────────────────────────────────────────────────────

    def add_callback(self, event_name, callback):
        """Đăng ký hàm lắng nghe sự kiện từ Server."""
        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback)

    def trigger_callback(self, event_name, *args, **kwargs):
        """Kích hoạt các hàm callback đã đăng ký một cách an toàn."""
        for cb in self.callbacks.get(event_name, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass

    def log(self, message, tag='INFO'):
        """Ghi nhận nhật ký ra console đồng thời phát tín hiệu cho GUI."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        self.trigger_callback('on_log', timestamp, message, tag)

    # ─────────────────────────────────────────────────────────────────
    # KHỞI ĐỘNG & TẮT SERVER
    # ─────────────────────────────────────────────────────────────────

    def start_threaded(self):
        """
        Khởi động Server trong một background thread (dành cho GUI
        để không làm đóng băng giao diện người dùng).
        """
        if self.running:
            return False, "Server đang hoạt động."

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            self.log(f"🚀 Máy chủ đã khởi động thành công trên {self.host}:{self.port}", tag='SUCCESS')
            self.trigger_callback('on_status', True, self.host, self.port)

            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            return True, f"Server đang lắng nghe tại {self.host}:{self.port}"

        except OSError as e:
            self.running = False
            err_text = f"Không thể lắng nghe trên {self.host}:{self.port}: {e}"
            self.log(f"❌ {err_text}", tag='ERROR')
            self.trigger_callback('on_status', False, self.host, self.port)
            return False, err_text

    def start(self):
        """Khởi động Server ở chế độ Console (CLI) truyền thống."""
        ok, msg = self.start_threaded()
        if not ok:
            print(f"[LỖI] {msg}")
            print("       Có thể port đã được sử dụng bởi chương trình khác.")
            return

        print("=" * 55)
        print("       TCP CHAT SERVER - QUẢN LÝ CLIENT ID")
        print("       Hỗ trợ nhiều Client (Multi-Client)")
        print("=" * 55)
        print(f"  Địa chỉ  : {self.host}")
        print(f"  Port     : {self.port}")
        print(f"  Trạng thái: Đang lắng nghe kết nối...")
        print(f"  Tắt Server: Nhấn Ctrl+C")
        print("=" * 55)

        try:
            # Giữ thread chính chạy cho tới khi nhận Ctrl+C
            while self.running:
                import time
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[SERVER] Nhận tín hiệu tắt (Ctrl+C)...")
        finally:
            self.shutdown()

    def shutdown(self):
        """Tắt Server và đóng tất cả các kết nối an toàn."""
        if not self.running and not self.server_socket:
            return

        self.running = False
        self.log("🛑 Đang đóng các kết nối và dừng Server...", tag='WARNING')

        with self.clients_lock:
            if self.clients:
                shutdown_msg = encode_message(MSG_SYSTEM, {
                    "message": "Server đang tắt. Kết nối sẽ bị ngắt."
                })
                for client_sock, session in list(self.clients.items()):
                    try:
                        client_sock.sendall(shutdown_msg)
                        client_sock.close()
                    except OSError:
                        pass
                    session.status = "🔴 Server tắt"
                    session.is_active = False
                    self.client_history.append(session)
                    self.trigger_callback('on_client_leave', session.to_dict())
                self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        self.log("✅ Server đã tắt hoàn toàn.", tag='SUCCESS')
        self.trigger_callback('on_status', False, self.host, self.port)

    # ─────────────────────────────────────────────────────────────────
    # XỬ LÝ KẾT NỐI & CLIENT
    # ─────────────────────────────────────────────────────────────────

    def _accept_connections(self):
        """Vòng lặp chấp nhận kết nối TCP từ Client."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
            except OSError:
                break

            with self.clients_lock:
                self.client_id_counter += 1
                self.total_connections += 1
                client_id = self.client_id_counter

                session = ClientSession(client_id, client_socket, client_address)
                self.clients[client_socket] = session

            self.log(
                f"🔌 [KẾT NỐI MỚI] Client ID #{client_id} kết nối từ {client_address[0]}:{client_address[1]} "
                f"(Socket FD: {session.fileno})",
                tag='CONNECT'
            )
            self.trigger_callback('on_client_connect', session.to_dict())

            client_thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket, session),
                daemon=True
            )
            client_thread.start()

    def _handle_client(self, client_socket, session):
        """Xử lý giao tiếp của một Client cụ thể."""
        client_id = session.id
        client_address = session.address
        username = None

        try:
            raw_data = client_socket.recv(BUFFER_SIZE)

            if not raw_data:
                self.log(f"⚠️ [NGẮT] Client ID #{client_id} ({client_address}) ngắt kết nối ngay", tag='WARNING')
                return

            messages = decode_messages(raw_data)

            if not messages or messages[0]['type'] != MSG_JOIN:
                error_msg = encode_message(MSG_ERROR, {
                    "message": "Bạn cần gửi lệnh JOIN trước khi chat."
                })
                client_socket.sendall(error_msg)
                client_socket.close()
                return

            username = messages[0]['data'].get('username', '').strip()

            # Kiểm tra username rỗng
            if not username:
                error_msg = encode_message(MSG_ERROR, {
                    "message": "Username không được để trống."
                })
                client_socket.sendall(error_msg)
                client_socket.close()
                return

            with self.clients_lock:
                existing_usernames = [
                    c.username for c in self.clients.values()
                    if c.username and c.is_active and c.id != client_id
                ]

                if username in existing_usernames:
                    error_msg = encode_message(MSG_ERROR, {
                        "message": f"Tên '{username}' đã được sử dụng. Vui lòng chọn tên khác."
                    })
                    client_socket.sendall(error_msg)
                    client_socket.close()
                    return

                # Cập nhật thông tin ClientSession
                session.username = username
                session.status = "🟢 Online"

            # Gửi WELCOME cho Client mới kèm ID được cấp
            welcome_msg = encode_message(MSG_WELCOME, {
                "message": f"Chào mừng {username} (ID: #{client_id}) đến phòng chat!",
                "client_id": client_id
            })
            client_socket.sendall(welcome_msg)

            # Thông báo cho các Client khác trong phòng
            join_notification = encode_message(MSG_SYSTEM, {
                "message": f"'{username}' (ID: #{client_id}) đã tham gia phòng chat."
            })
            self._broadcast(join_notification, exclude=client_socket)
            self._broadcast_online_list()

            online_count = self._get_online_count()
            self.log(
                f"👤 [THAM GIA] Client ID #{client_id} đăng ký tên '{username}'. Online: {online_count} người",
                tag='JOIN'
            )
            self.trigger_callback('on_client_join', session.to_dict())

            # Vòng lặp nhận tin nhắn từ Client
            while self.running:
                raw_data = client_socket.recv(BUFFER_SIZE)

                if not raw_data:
                    self.log(f"🚪 [NGẮT] Client ID #{client_id} ('{username}') đã ngắt kết nối", tag='LEAVE')
                    break

                messages = decode_messages(raw_data)

                for msg in messages:
                    msg_type = msg.get('type')

                    if msg_type == MSG_MSG:
                        # ── Tin nhắn chat chung ──
                        content = msg['data'].get('content', '')
                        timestamp = datetime.now().strftime("%H:%M:%S")

                        session.msg_count += 1
                        self.total_messages += 1

                        self.log(f"💬 [CHAT] [ID #{client_id}] {username}: {content}", tag='CHAT')
                        self.trigger_callback('on_message', {
                            'type': MSG_MSG,
                            'client_id': client_id,
                            'username': username,
                            'content': content,
                            'timestamp': timestamp
                        })
                        self.trigger_callback('on_client_update', session.to_dict())

                        chat_msg = encode_message(MSG_MSG, {
                            "username": username,
                            "content": content,
                            "timestamp": timestamp,
                            "client_id": client_id
                        })
                        self._broadcast(chat_msg)

                    elif msg_type == MSG_PRIVATE:
                        # ── Tin nhắn chat riêng (Whisper/PM) ──
                        target_user = msg['data'].get('to', '').strip()
                        content = msg['data'].get('content', '').strip()
                        timestamp = datetime.now().strftime("%H:%M:%S")

                        session.msg_count += 1
                        self.total_messages += 1

                        if not target_user or not content:
                            err_msg = encode_message(MSG_ERROR, {
                                "message": "Tin nhắn riêng cần chỉ định người nhận và nội dung."
                            })
                            client_socket.sendall(err_msg)
                            continue

                        if target_user == username:
                            err_msg = encode_message(MSG_ERROR, {
                                "message": "Bạn không thể gửi tin nhắn riêng cho chính mình."
                            })
                            client_socket.sendall(err_msg)
                            continue

                        # Tìm socket và session của người nhận
                        target_sock = None
                        target_session = None
                        with self.clients_lock:
                            for sock, sess in self.clients.items():
                                if sess.username == target_user and sess.is_active:
                                    target_sock = sock
                                    target_session = sess
                                    break

                        if target_sock and target_session:
                            self.log(
                                f"🔒 [RIÊNG] [ID #{client_id}] {username} -> [ID #{target_session.id}] {target_user}: {content}",
                                tag='PRIVATE'
                            )
                            self.trigger_callback('on_message', {
                                'type': MSG_PRIVATE,
                                'from_id': client_id,
                                'from_user': username,
                                'to_id': target_session.id,
                                'to_user': target_user,
                                'content': content,
                                'timestamp': timestamp
                            })
                            self.trigger_callback('on_client_update', session.to_dict())

                            # Gửi tới người nhận
                            dm_target = encode_message(MSG_PRIVATE, {
                                "from": username,
                                "to": target_user,
                                "content": content,
                                "timestamp": timestamp,
                                "is_sender": False,
                                "sender_id": client_id
                            })
                            try:
                                target_sock.sendall(dm_target)
                            except OSError:
                                pass

                            # Gửi phản hồi tới người gửi để xác nhận
                            dm_sender = encode_message(MSG_PRIVATE, {
                                "from": username,
                                "to": target_user,
                                "content": content,
                                "timestamp": timestamp,
                                "is_sender": True
                            })
                            try:
                                client_socket.sendall(dm_sender)
                            except OSError:
                                pass
                        else:
                            err_msg = encode_message(MSG_ERROR, {
                                "message": f"Không tìm thấy người dùng '{target_user}' đang online."
                            })
                            try:
                                client_socket.sendall(err_msg)
                            except OSError:
                                pass

                    elif msg_type == MSG_QUIT:
                        # ── Client thông báo thoát ──
                        self.log(f"🚪 [THOÁT] Client ID #{client_id} ('{username}') đã thông báo rời phòng", tag='LEAVE')
                        return

                    else:
                        self.log(
                            f"❓ [CẢNH BÁO] Tin nhắn không xác định từ Client ID #{client_id} ('{username}'): {msg_type}",
                            tag='WARNING'
                        )

        except ConnectionResetError:
            self.log(f"⚡ [LỖI] Client ID #{client_id} ('{username or client_address}') mất kết nối đột ngột", tag='ERROR')

        except ConnectionAbortedError:
            self.log(f"⚡ [LỖI] Kết nối Client ID #{client_id} ('{username or client_address}') bị hủy", tag='ERROR')

        except Exception as e:
            self.log(f"⚡ [LỖI] Lỗi xử lý Client ID #{client_id} ('{username or client_address}'): {e}", tag='ERROR')

        finally:
            self._remove_client(client_socket, session)

    def _broadcast(self, message_bytes, exclude=None):
        """Phát tin nhắn tới tất cả Client đang online."""
        with self.clients_lock:
            disconnected = []

            for client_sock, session in list(self.clients.items()):
                if client_sock is exclude or not session.is_active:
                    continue

                try:
                    client_sock.sendall(message_bytes)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    disconnected.append((client_sock, session))

            # Xử lý các Client bị đứt kết nối
            for sock, session in disconnected:
                session.status = "🔴 Mất kết nối"
                session.is_active = False
                self.clients.pop(sock, None)
                self.client_history.append(session)
                self.trigger_callback('on_client_leave', session.to_dict())
                self.log(
                    f"🧹 [CLEANUP] Đã xóa Client ID #{session.id} ('{session.username}') do mất kết nối broadcast",
                    tag='WARNING'
                )

    def _remove_client(self, client_socket, session):
        """Xóa Client khỏi danh sách và thông báo cho mọi người."""
        with self.clients_lock:
            if client_socket in self.clients:
                session.status = "🔴 Đã ngắt"
                session.is_active = False
                del self.clients[client_socket]
                self.client_history.append(session)

        try:
            client_socket.close()
        except OSError:
            pass

        self.trigger_callback('on_client_leave', session.to_dict())

        if session.username:
            leave_notification = encode_message(MSG_SYSTEM, {
                "message": f"'{session.username}' (ID: #{session.id}) đã rời phòng chat."
            })
            self._broadcast(leave_notification)

            online_count = self._get_online_count()
            self.log(
                f"🔌 [ĐÓNG] Đã đóng kết nối Client ID #{session.id} ('{session.username}'). Online: {online_count} người",
                tag='LEAVE'
            )
            self._broadcast_online_list()
        else:
            self.log(
                f"🔌 [ĐÓNG] Đã đóng kết nối chưa đăng nhập của Client ID #{session.id}",
                tag='LEAVE'
            )

    def _broadcast_online_list(self):
        """Gửi danh sách người dùng online tới tất cả Client."""
        with self.clients_lock:
            online_users = [
                c.username for c in self.clients.values()
                if c.username and c.is_active
            ]

        online_msg = encode_message(MSG_ONLINE_LIST, {
            "users": online_users
        })
        self._broadcast(online_msg)

    def _get_online_count(self):
        """Đếm số lượng Client đã đăng nhập và đang hoạt động."""
        with self.clients_lock:
            return len([c for c in self.clients.values() if c.username and c.is_active])

    # ─────────────────────────────────────────────────────────────────
    # THAO TÁC QUẢN TRỊ DÀNH CHO GIAO DIỆN SERVER (GUI ACTIONS)
    # ─────────────────────────────────────────────────────────────────

    def kick_client(self, client_id, reason="Quản trị viên đã ngắt kết nối của bạn."):
        """Ngắt kết nối cưỡng chế một Client theo Client ID."""
        target_sock = None
        target_session = None

        with self.clients_lock:
            for sock, sess in self.clients.items():
                if sess.id == client_id:
                    target_sock = sock
                    target_session = sess
                    break

        if target_sock and target_session:
            self.log(
                f"👢 [KICK] Quản trị viên ngắt kết nối Client ID #{client_id} ('{target_session.username}') - Lý do: {reason}",
                tag='WARNING'
            )
            try:
                err_msg = encode_message(MSG_ERROR, {
                    "message": f"Bạn đã bị ngắt kết nối bởi Quản trị viên: {reason}"
                })
                target_sock.sendall(err_msg)
            except OSError:
                pass

            self._remove_client(target_sock, target_session)
            return True, f"Đã ngắt kết nối Client ID #{client_id}"

        return False, f"Không tìm thấy Client ID #{client_id} đang kết nối."

    def broadcast_announcement(self, message_text):
        """Gửi thông báo hệ thống từ Quản trị viên tới tất cả Client."""
        text = message_text.strip()
        if not text:
            return False, "Nội dung thông báo không được để trống."

        timestamp = datetime.now().strftime("%H:%M:%S")
        content = f"[THÔNG BÁO TỪ QUẢN TRỊ VIÊN SERVER]: {text}"

        announcement_bytes = encode_message(MSG_SYSTEM, {
            "message": content
        })
        self._broadcast(announcement_bytes)
        self.total_messages += 1

        self.log(f"📢 [THÔNG BÁO QUẢN TRỊ VIÊN] {text}", tag='SYSTEM')
        self.trigger_callback('on_message', {
            'type': MSG_SYSTEM,
            'client_id': 'SERVER',
            'username': 'SERVER ADMIN',
            'content': content,
            'timestamp': timestamp
        })
        return True, "Đã gửi thông báo thành công."

    def send_private_admin(self, client_id, message_text):
        """Gửi tin nhắn riêng từ Quản trị viên tới một Client ID cụ thể."""
        text = message_text.strip()
        if not text:
            return False, "Nội dung tin nhắn không được để trống."

        target_sock = None
        target_session = None

        with self.clients_lock:
            for sock, sess in self.clients.items():
                if sess.id == client_id:
                    target_sock = sock
                    target_session = sess
                    break

        if target_sock and target_session:
            timestamp = datetime.now().strftime("%H:%M:%S")
            content = f"[ADMIN NHẮN RIÊNG]: {text}"
            msg_bytes = encode_message(MSG_PRIVATE, {
                "from": "QUẢN TRỊ VIÊN SERVER",
                "to": target_session.username or f"Client #{client_id}",
                "content": content,
                "timestamp": timestamp,
                "is_sender": False
            })
            try:
                target_sock.sendall(msg_bytes)
            except OSError:
                return False, "Lỗi khi gửi socket tới Client."

            self.log(
                f"🔒 [ADMIN -> ID #{client_id} ('{target_session.username}')]: {text}",
                tag='PRIVATE'
            )
            return True, f"Đã gửi tin nhắn riêng tới Client ID #{client_id}."

        return False, f"Không tìm thấy Client ID #{client_id} đang kết nối."

    def get_clients_list(self):
        """Lấy danh sách thông tin tất cả Client đang kết nối."""
        with self.clients_lock:
            return [sess.to_dict() for sess in self.clients.values()]

    def get_stats(self):
        """Lấy thông số thống kê tổng quan của Server."""
        with self.clients_lock:
            online_count = len([c for c in self.clients.values() if c.username and c.is_active])
            connecting_count = len([c for c in self.clients.values() if not c.username and c.is_active])
            return {
                "online": online_count,
                "connecting": connecting_count,
                "total_active": len(self.clients),
                "total_connections": self.total_connections,
                "total_messages": self.total_messages
            }
