"""
Web Server & Dual-Protocol Bridge cho Seminar Lập Trình Mạng (Client - Server).
Đồng thời hỗ trợ:
1. Giao diện Web Client & Admin Dashboard qua HTTP & WebSocket (Port 8080).
2. Socket TCP truyền thống (Port 9000) tương thích 100% với run_gui.py & run_client.py.
3. Đồng bộ tin nhắn tập trung giữa cả 2 nền tảng Web & Desktop TCP.
"""

import os
import sys
import json
import time
import socket
import asyncio
from datetime import datetime
from aiohttp import web, WSMsgType

# Thêm thư mục gốc vào sys.path để import common và config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
from common.protocol import (
    MSG_JOIN, MSG_MSG, MSG_PRIVATE, MSG_QUIT,
    MSG_WELCOME, MSG_SYSTEM, MSG_ERROR, MSG_ONLINE_LIST,
    create_message, parse_message, encode_message, decode_messages
)
from server.auth import auth_manager
from server.rooms import room_manager, MeetingRoom

# Cấu hình cổng mặc định
TCP_PORT = getattr(config, 'PORT', 9000)
WEB_PORT = getattr(config, 'WEB_PORT', 8080)
HOST = getattr(config, 'HOST', '0.0.0.0')
BUFFER_SIZE = getattr(config, 'BUFFER_SIZE', 4096)
ENCODING = getattr(config, 'ENCODING', 'utf-8')


class WebClientSession:
    """Đại diện cho phiên kết nối của một Client (qua WebSocket hoặc TCP)."""

    def __init__(self, client_id, client_type, address, ws=None, reader=None, writer=None):
        self.id = client_id
        self.client_type = client_type  # 'websocket' hoặc 'tcp'
        self.address = address
        self.ip = address[0] if isinstance(address, (list, tuple)) and len(address) > 0 else str(address)
        self.port = address[1] if isinstance(address, (list, tuple)) and len(address) > 1 else 0
        self.username = None
        self.fullname = None
        self.avatar_color = None
        self.is_host = False
        self.room_code = "seminar-network-lab"
        self.connected_at = datetime.now()
        self.ws = ws
        self.reader = reader
        self.writer = writer
        self.msg_count = 0
        self.status = "Chờ JOIN"
        self.is_active = True
        self.is_muted = False
        self.media_state = {"mic": True, "cam": True, "screen": False, "hand": False}
        self.bytes_sent = 0
        self.bytes_received = 0

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.client_type,
            "username": self.username or "(Chờ JOIN)",
            "fullname": self.fullname or self.username or "(Chờ JOIN)",
            "avatar_color": self.avatar_color or "#6366F1",
            "is_host": self.is_host,
            "room_code": self.room_code,
            "ip": self.ip,
            "port": self.port,
            "address": f"{self.ip}:{self.port}",
            "connected_at": self.connected_at.strftime("%H:%M:%S"),
            "connected_timestamp": self.connected_at.isoformat(),
            "status": self.status,
            "msg_count": self.msg_count,
            "is_active": self.is_active,
            "is_muted": self.is_muted,
            "media_state": getattr(self, 'media_state', {"mic": True, "cam": True, "screen": False, "hand": False})
        }


class DualChatHub:
    """Trung tâm điều phối tin nhắn đa giao thức (WebSocket + TCP Socket)."""

    def __init__(self):
        self.client_id_counter = 0
        self.clients = {}  # id -> WebClientSession
        self.admin_websockets = set()
        self.start_time = datetime.now()
        self.total_connections = 0
        self.total_messages = 0
        self.total_bytes_transferred = 0
        self.logs = []
        self.max_logs = 500
        self.lock = asyncio.Lock()
        self.room_manager = room_manager

        # Quản lý phòng họp / Host Controls (Google Meet / Zoom style)
        self.is_room_locked = False
        self.allow_public_chat = True
        self.allow_private_chat = True

    def log(self, message, tag='INFO'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "tag": tag
        }
        print(f"[{timestamp}] [{tag:7s}] {message}")
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

        # Gửi log ngay cho các Admin WebSockets đang mở
        asyncio.create_task(self._notify_admins('LOG', log_entry))

    async def _notify_admins(self, event_type, data, room_code=None, **kwargs):
        """Gửi thông báo sự kiện theo thời gian thực tới tất cả Admin Dashboard."""
        if not self.admin_websockets:
            return

        payload_dict = {"event": event_type, "data": data}
        if room_code:
            payload_dict["room"] = room_code
        payload = json.dumps(payload_dict, ensure_ascii=False)
        closed = set()
        for ws in self.admin_websockets:
            try:
                if not ws.closed:
                    await ws.send_str(payload)
                else:
                    closed.add(ws)
            except Exception:
                closed.add(ws)

        self.admin_websockets.difference_update(closed)

    def get_stats(self):
        uptime_seconds = int((datetime.now() - self.start_time).total_seconds())
        online_clients = [c for c in self.clients.values() if c.is_active and c.username]
        tcp_count = len([c for c in online_clients if c.client_type == 'tcp'])
        ws_count = len([c for c in online_clients if c.client_type == 'websocket'])

        return {
            "uptime_seconds": uptime_seconds,
            "uptime_str": time.strftime("%H:%M:%S", time.gmtime(uptime_seconds)),
            "online_total": len(online_clients),
            "online_tcp": tcp_count,
            "online_ws": ws_count,
            "total_active": len(self.clients),
            "total_connections": self.total_connections,
            "total_messages": self.total_messages,
            "bytes_transferred": self.total_bytes_transferred,
            "tcp_port": TCP_PORT,
            "web_port": WEB_PORT,
            "is_room_locked": self.is_room_locked,
            "allow_public_chat": self.allow_public_chat,
            "allow_private_chat": self.allow_private_chat
        }

    def get_online_usernames(self):
        return [c.username for c in self.clients.values() if c.is_active and c.username]

    def get_online_users_detail(self):
        return [
            {
                "id": c.id,
                "username": c.username,
                "type": c.client_type,
                "ip": c.ip,
                "connected_at": c.connected_at.strftime("%H:%M:%S"),
                "is_muted": c.is_muted
            }
            for c in self.clients.values()
            if c.is_active and c.username
        ]

    async def send_to_session(self, session, msg_type, data):
        """Gửi gói tin tới một Client Session cụ thể (tự động phân nhánh WebSocket/TCP)."""
        if not session.is_active:
            return False

        try:
            if session.client_type == 'websocket' and session.ws:
                if not session.ws.closed:
                    json_str = create_message(msg_type, data)
                    await session.ws.send_str(json_str)
                    session.bytes_sent += len(json_str.encode(ENCODING))
                    self.total_bytes_transferred += len(json_str.encode(ENCODING))
                    return True
            elif session.client_type == 'tcp' and session.writer:
                raw_bytes = encode_message(msg_type, data)
                session.writer.write(raw_bytes)
                await session.writer.drain()
                session.bytes_sent += len(raw_bytes)
                self.total_bytes_transferred += len(raw_bytes)
                return True
        except Exception as e:
            self.log(f"Lỗi khi gửi tới Client #{session.id} ({session.username}): {e}", tag='ERROR')
            session.is_active = False

        return False

    async def broadcast(self, msg_type, data, exclude_id=None, room_code=None):
        """Gửi gói tin tới TẤT CẢ các Client trong cùng phòng họp (hoặc toàn bộ nếu room_code=None)."""
        tasks = []
        for session in list(self.clients.values()):
            if session.id == exclude_id or not session.is_active or not session.username:
                continue
            if room_code and getattr(session, 'room_code', None) != room_code:
                continue
            tasks.append(self.send_to_session(session, msg_type, data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_online_list(self, room_code=None):
        """Cập nhật danh sách người dùng online tới các Client trong phòng & Admin."""
        target_rooms = [room_code] if room_code else list(set(getattr(c, 'room_code', 'seminar-network-lab') for c in self.clients.values()))
        if not target_rooms:
            target_rooms = ['seminar-network-lab']

        for r_code in target_rooms:
            room_clients = [c for c in self.clients.values() if c.is_active and c.username and getattr(c, 'room_code', 'seminar-network-lab') == r_code]
            usernames = [c.username for c in room_clients]
            users_detail = [c.to_dict() for c in room_clients]

            payload = {
                "users": usernames,
                "users_detail": users_detail,
                "room": r_code
            }
            await self.broadcast(MSG_ONLINE_LIST, payload, room_code=r_code)

        # Cập nhật cho Admin Dashboard
        await self._notify_admins('CLIENTS_UPDATE', [c.to_dict() for c in self.clients.values()], room_code=room_code)
        await self._notify_admins('STATS_UPDATE', self.get_stats())

    async def register_client(self, client_type, address, ws=None, reader=None, writer=None):
        """Khởi tạo phiên kết nối mới và cấp phát Client ID."""
        async with self.lock:
            self.client_id_counter += 1
            self.total_connections += 1
            client_id = self.client_id_counter

            session = WebClientSession(
                client_id=client_id,
                client_type=client_type,
                address=address,
                ws=ws,
                reader=reader,
                writer=writer
            )
            self.clients[client_id] = session

        self.log(
            f"🔌 [{client_type.upper()}] Client ID #{client_id} kết nối từ {session.address}",
            tag='CONNECT'
        )
        await self._notify_admins('CLIENT_CONNECT', session.to_dict())
        await self._notify_admins('STATS_UPDATE', self.get_stats())
        return session

    async def handle_join(self, session, username, room_code="seminar-network-lab", token=None):
        """Xử lý đăng ký tên người dùng (lệnh JOIN) vào phòng họp cụ thể."""
        room_code = (room_code or getattr(session, 'room_code', 'seminar-network-lab')).strip().lower()
        session.room_code = room_code

        room = self.room_manager.get_or_create_room(room_code)

        # Kiểm tra token xác thực nếu có
        user_info = None
        if token:
            user_info = auth_manager.get_user_by_token(token)
            if user_info:
                session.fullname = user_info.get('fullname')
                session.avatar_color = user_info.get('avatar_color')
                if user_info.get('username') == room.host_username or user_info.get('role') in ['admin', 'host']:
                    session.is_host = True

        # Kiểm tra nếu phòng đang bị khóa bởi Host
        if (room.is_locked or self.is_room_locked) and not session.is_host:
            await self.send_to_session(session, MSG_ERROR, {
                "message": f"Phòng họp '{room.code}' hiện đang bị khóa bởi Host (Chủ trì)."
            })
            return False

        username = (username or '').strip()
        if not username:
            if user_info:
                username = user_info.get('username')
            else:
                await self.send_to_session(session, MSG_ERROR, {
                    "message": "Tên người dùng không được để trống."
                })
                return False

        # Kiểm tra trùng lặp username trong cùng phòng họp
        existing_names = [
            c.username for c in self.clients.values()
            if c.username and c.is_active and c.id != session.id and getattr(c, 'room_code', '') == room_code
        ]
        if username in existing_names:
            await self.send_to_session(session, MSG_ERROR, {
                "message": f"Tên '{username}' đã được sử dụng trong phòng này. Vui lòng chọn tên khác."
            })
            return False

        session.username = username
        session.status = "🟢 Online"
        room.add_client(session)

        # Gửi WELCOME cho Client mới kèm ID được cấp
        await self.send_to_session(session, MSG_WELCOME, {
            "message": f"Chào mừng {session.fullname or username} (ID: #{session.id}) đến phòng họp '{room.title}'!",
            "client_id": session.id,
            "client_type": session.client_type,
            "username": username,
            "fullname": session.fullname or username,
            "room_code": room_code,
            "room_title": room.title,
            "is_host": session.is_host,
            "avatar_color": session.avatar_color or "#6366F1"
        })

        # Báo cho các Client khác trong phòng
        platform_icon = "🌐 Web" if session.client_type == 'websocket' else "💻 Desktop TCP"
        join_notification = {
            "message": f"'{session.fullname or username}' (ID: #{session.id} - {platform_icon}) đã tham gia phòng họp.",
            "client_id": session.id,
            "username": username,
            "fullname": session.fullname or username,
            "room": room_code
        }
        await self.broadcast(MSG_SYSTEM, join_notification, exclude_id=session.id, room_code=room_code)
        await self.broadcast_online_list(room_code=room_code)

        online_count = len([c for c in self.clients.values() if c.is_active and c.username and getattr(c, 'room_code', '') == room_code])
        self.log(
            f"👤 [THAM GIA] #{session.id} '{username}' vào phòng [{room_code}]. Online phòng: {online_count}",
            tag='JOIN'
        )
        await self._notify_admins('CLIENT_JOIN', session.to_dict(), room_code=room_code)
        return True

    async def handle_chat_message(self, session, content):
        """Xử lý tin nhắn chat công khai (MSG)."""
        if not session.username:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Bạn cần JOIN trước khi gửi tin nhắn."
            })
            return

        room = self.room_manager.get_room(getattr(session, 'room_code', 'seminar-network-lab'))

        # Kiểm tra quyền Host controls
        if session.is_muted:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Bạn đã bị Host tắt quyền gửi tin nhắn trong phòng."
            })
            return

        if room and not room.allow_public_chat and not session.is_host:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Host đã tạm thời khóa tính năng chat chung trong phòng này."
            })
            return

        content = (content or '').strip()
        if not content:
            return

        session.msg_count += 1
        self.total_messages += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.log(f"💬 [{session.room_code}] #{session.id} {session.username}: {content}", tag='CHAT')

        msg_payload = {
            "username": session.username,
            "fullname": session.fullname or session.username,
            "content": content,
            "timestamp": timestamp,
            "client_id": session.id,
            "client_type": session.client_type,
            "avatar_color": session.avatar_color or "#6366F1",
            "is_host": session.is_host,
            "room": session.room_code
        }

        if room:
            room.add_chat(msg_payload)

        # Phát cho các client trong cùng phòng
        await self.broadcast(MSG_MSG, msg_payload, room_code=session.room_code)

        # Cập nhật cho Admin Dashboard
        await self._notify_admins('MESSAGE', {
            "type": MSG_MSG,
            **msg_payload
        }, room_code=session.room_code)
        await self._notify_admins('STATS_UPDATE', self.get_stats())

    async def handle_private_message(self, session, target_user, content):
        """Xử lý tin nhắn riêng tư (PRIVATE / Whisper) trong cùng phòng."""
        if not session.username:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Bạn cần JOIN trước khi gửi tin nhắn riêng."
            })
            return

        # Kiểm tra quyền Host controls
        if session.is_muted:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Bạn đã bị Host tắt quyền gửi tin nhắn."
            })
            return

        room = self.room_manager.get_room(getattr(session, 'room_code', 'seminar-network-lab'))
        if room and not room.allow_private_chat and not session.is_host:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Host đã tạm thời tắt tính năng chat riêng 1-1 trong phòng này."
            })
            return

        target_user = (target_user or '').strip()
        content = (content or '').strip()
        timestamp = datetime.now().strftime("%H:%M:%S")

        if not target_user or not content:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Tin nhắn riêng cần chỉ định người nhận và nội dung."
            })
            return

        if target_user == session.username:
            await self.send_to_session(session, MSG_ERROR, {
                "message": "Bạn không thể gửi tin nhắn riêng cho chính mình."
            })
            return

        # Tìm người nhận trong CÙNG phòng
        target_session = None
        for s in self.clients.values():
            if s.is_active and s.username == target_user and getattr(s, 'room_code', '') == session.room_code:
                target_session = s
                break

        if not target_session:
            await self.send_to_session(session, MSG_ERROR, {
                "message": f"Không tìm thấy người dùng '{target_user}' trong phòng họp này."
            })
            return

        session.msg_count += 1
        self.total_messages += 1

        self.log(
            f"🔒 [RIÊNG] [{session.room_code}] #{session.id} {session.username} -> #{target_session.id} {target_user}: {content}",
            tag='PRIVATE'
        )

        # Gửi cho người nhận
        dm_target = {
            "from": session.username,
            "to": target_user,
            "content": content,
            "timestamp": timestamp,
            "is_sender": False,
            "sender_id": session.id,
            "sender_type": session.client_type,
            "room": session.room_code
        }
        await self.send_to_session(target_session, MSG_PRIVATE, dm_target)

        # Gửi lại người gửi để xác nhận (Hiển thị bong bóng bên mình)
        dm_sender = {
            "from": session.username,
            "to": target_user,
            "content": content,
            "timestamp": timestamp,
            "is_sender": True,
            "sender_id": session.id,
            "sender_type": session.client_type,
            "room": session.room_code
        }
        await self.send_to_session(session, MSG_PRIVATE, dm_sender)

        # Thông báo Admin
        await self._notify_admins('MESSAGE', {
            "type": MSG_PRIVATE,
            "from_id": session.id,
            "from_user": session.username,
            "to_id": target_session.id,
            "to_user": target_user,
            "content": content,
            "timestamp": timestamp,
            "room": session.room_code
        }, room_code=session.room_code)
        await self._notify_admins('STATS_UPDATE', self.get_stats())

    async def remove_client(self, session, reason="Đã ngắt kết nối"):
        """Đóng kết nối và gỡ Client khỏi hệ thống."""
        if not session.is_active:
            return

        session.is_active = False
        session.status = f"🔴 {reason}"

        username = session.username
        client_id = session.id
        client_type = session.client_type
        room_code = getattr(session, 'room_code', 'seminar-network-lab')

        # Gỡ khỏi phòng họp
        room = self.room_manager.get_room(room_code)
        if room:
            room.remove_client(session)
            if room.online_count == 0:
                if room_code != 'seminar-network-lab':
                    self.room_manager.delete_room(room_code)
                self.log(
                    f"🛑 [PHÒNG NGẮT] Phòng [{room_code}] đã tự động ngắt/kết thúc vì không còn ai tham gia.",
                    tag='ROOM'
                )

        # Đóng socket tương ứng
        try:
            if session.client_type == 'websocket' and session.ws and not session.ws.closed:
                await session.ws.close()
            elif session.client_type == 'tcp' and session.writer:
                session.writer.close()
                await session.writer.wait_closed()
        except Exception:
            pass

        # Xóa khỏi danh sách hoạt động
        self.clients.pop(client_id, None)

        if username:
            self.log(
                f"🚪 [RỜI PHÒNG] [{room_code}] #{client_id} '{username}' rời phòng ({reason})",
                tag='LEAVE'
            )
            leave_msg = {
                "message": f"'{session.fullname or username}' (ID: #{client_id}) đã rời phòng họp.",
                "client_id": client_id,
                "username": username,
                "room": room_code
            }
            await self.broadcast(MSG_SYSTEM, leave_msg, room_code=room_code)
            await self.broadcast_online_list(room_code=room_code)
        else:
            self.log(f"🚪 [NGẮT] Client #{client_id} ngắt kết nối chưa JOIN", tag='LEAVE')

        await self._notify_admins('CLIENT_LEAVE', session.to_dict(), room_code=room_code)
        await self._notify_admins('STATS_UPDATE', self.get_stats())

    async def admin_kick(self, client_id, reason="Quản trị viên đã ngắt kết nối."):
        """Quản trị viên ngắt kết nối cưỡng chế Client."""
        session = self.clients.get(client_id)
        if not session or not session.is_active:
            return False, f"Không tìm thấy Client ID #{client_id}"

        self.log(f"👢 [KICK] Admin ngắt kết nối Client #{client_id} ('{session.username}') - Lý do: {reason}", tag='WARNING')

        # Gửi thông báo lỗi trước khi ngắt
        await self.send_to_session(session, MSG_ERROR, {
            "message": f"Bạn đã bị ngắt kết nối bởi Quản trị viên: {reason}"
        })

        await self.remove_client(session, reason=f"Bị Kick: {reason}")
        return True, f"Đã ngắt kết nối Client #{client_id}"

    async def admin_broadcast(self, text):
        """Quản trị viên gửi thông báo toàn hệ thống."""
        text = (text or '').strip()
        if not text:
            return False, "Nội dung không được để trống"

        timestamp = datetime.now().strftime("%H:%M:%S")
        content = f"[THÔNG BÁO TỪ QUẢN TRỊ VIÊN]: {text}"

        msg_payload = {
            "message": content,
            "is_admin_announcement": True,
            "timestamp": timestamp
        }

        await self.broadcast(MSG_SYSTEM, msg_payload)
        self.total_messages += 1

        self.log(f"📢 [THÔNG BÁO QUẢN TRỊ] {text}", tag='SYSTEM')
        await self._notify_admins('MESSAGE', {
            "type": MSG_SYSTEM,
            "client_id": "ADMIN",
            "username": "HỆ THỐNG",
            "content": content,
            "timestamp": timestamp
        })
        await self._notify_admins('STATS_UPDATE', self.get_stats())
        return True, "Đã gửi thông báo thành công"

    async def admin_direct_message(self, client_id, text):
        """Quản trị viên gửi tin nhắn riêng cho một Client."""
        session = self.clients.get(client_id)
        if not session or not session.is_active:
            return False, f"Không tìm thấy Client ID #{client_id}"

        text = (text or '').strip()
        if not text:
            return False, "Nội dung không được để trống"

        timestamp = datetime.now().strftime("%H:%M:%S")
        content = f"[ADMIN NHẮN RIÊNG]: {text}"

        msg_payload = {
            "from": "QUẢN TRỊ VIÊN SERVER",
            "to": session.username or f"Client #{client_id}",
            "content": content,
            "timestamp": timestamp,
            "is_sender": False,
            "is_admin": True
        }

        await self.send_to_session(session, MSG_PRIVATE, msg_payload)
        self.log(f"🔒 [ADMIN -> #{client_id} '{session.username}']: {text}", tag='PRIVATE')
        return True, f"Đã gửi tin nhắn tới #{client_id}"

    async def admin_toggle_lock(self):
        """Khóa hoặc mở khóa phòng (Google Meet / Zoom style)."""
        self.is_room_locked = not self.is_room_locked
        state_text = "🔒 ĐÃ KHÓA PHÒNG" if self.is_room_locked else "🔓 ĐÃ MỞ KHÓA PHÒNG"
        self.log(f"🛡️ [HOST CONTROL] Quản trị viên {state_text}", tag='SYSTEM')

        notice = "Host đã KHÓA PHÒNG (tạm dừng nhận thêm người tham gia mới)." if self.is_room_locked else "Host đã MỞ KHÓA PHÒNG."
        await self.broadcast(MSG_SYSTEM, {"message": f"[BẢO MẬT CUỘC HỌP]: {notice}"})
        await self._notify_admins('STATS_UPDATE', self.get_stats())
        return True, state_text

    async def admin_toggle_public_chat(self):
        """Bật hoặc tắt tính năng chat chung toàn phòng."""
        self.allow_public_chat = not self.allow_public_chat
        state_text = "ĐÃ MỞ CHAT CHUNG" if self.allow_public_chat else "ĐÃ KHÓA CHAT CHUNG"
        self.log(f"🛡️ [HOST CONTROL] Quản trị viên {state_text}", tag='SYSTEM')

        notice = "Host đã MỞ LẠI chat chung." if self.allow_public_chat else "Host đã TẮT tính năng chat chung trong phòng."
        await self.broadcast(MSG_SYSTEM, {"message": f"[QUYỀN PHÒNG]: {notice}"})
        await self._notify_admins('STATS_UPDATE', self.get_stats())
        return True, state_text

    async def admin_toggle_private_chat(self):
        """Bật hoặc tắt tính năng chat riêng 1-1."""
        self.allow_private_chat = not self.allow_private_chat
        state_text = "ĐÃ MỞ CHAT RIÊNG" if self.allow_private_chat else "ĐÃ KHÓA CHAT RIÊNG"
        self.log(f"🛡️ [HOST CONTROL] Quản trị viên {state_text}", tag='SYSTEM')

        notice = "Host đã MỞ LẠI tính năng chat riêng 1-1." if self.allow_private_chat else "Host đã TẮT tính năng chat riêng 1-1."
        await self.broadcast(MSG_SYSTEM, {"message": f"[QUYỀN PHÒNG]: {notice}"})
        await self._notify_admins('STATS_UPDATE', self.get_stats())
        return True, state_text

    async def admin_toggle_mute_client(self, client_id):
        """Bật hoặc tắt quyền chat của một Client cụ thể (Mute/Unmute)."""
        session = self.clients.get(client_id)
        if not session or not session.is_active:
            return False, f"Không tìm thấy Client #{client_id}"

        session.is_muted = not session.is_muted
        state_text = "🔇 ĐÃ TẮT QUYỀN CHAT" if session.is_muted else "🔊 ĐÃ MỞ LẠI QUYỀN CHAT"
        self.log(f"🔇 [HOST CONTROL] Host {state_text} Client #{client_id} ('{session.username}')", tag='WARNING')

        if session.is_muted:
            await self.send_to_session(session, MSG_ERROR, {"message": "🔇 Bạn đã bị Host tắt quyền gửi tin nhắn trong phòng."})
        else:
            await self.send_to_session(session, MSG_SYSTEM, {"message": "🔊 Bạn đã được Host mở lại quyền gửi tin nhắn trong phòng."})

        await self._notify_admins('CLIENTS_UPDATE', [c.to_dict() for c in self.clients.values()])
        return True, f"Client #{client_id} {state_text}"

    async def admin_mute_all(self):
        """Tắt quyền chat của tất cả thành viên trong phòng (Mute All)."""
        for s in self.clients.values():
            if s.is_active:
                s.is_muted = True
        self.log("🔇 [HOST CONTROL] Host đã tắt quyền chat của toàn bộ thành viên", tag='WARNING')
        await self.broadcast(MSG_SYSTEM, {"message": "🔇 [THÔNG BÁO TỪ HOST]: Tất cả người tham gia đã bị tắt quyền chat."})
        await self._notify_admins('CLIENTS_UPDATE', [c.to_dict() for c in self.clients.values()])
        return True, "Đã Mute Chat toàn bộ thành viên"


# ─────────────────────────────────────────────────────────────────
# HANDLERS GIAO THỨC WEBSOCKET
# ─────────────────────────────────────────────────────────────────

async def websocket_client_handler(request):
    """Xử lý kết nối WebSocket từ trình duyệt Web Client."""
    hub = request.app['hub']
    ws = web.WebSocketResponse(heartbeat=25.0)
    await ws.prepare(request)

    room_code = request.query.get('room', 'seminar-network-lab').strip().lower()
    token = request.query.get('token', '').strip()

    client_address = request.remote or "WebClient"
    session = await hub.register_client(
        client_type='websocket',
        address=(client_address, 0),
        ws=ws
    )
    session.room_code = room_code

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                raw_text = msg.data.strip()
                if not raw_text:
                    continue

                session.bytes_received += len(raw_text.encode(ENCODING))
                hub.total_bytes_transferred += len(raw_text.encode(ENCODING))

                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError:
                    await hub.send_to_session(session, MSG_ERROR, {"message": "Dữ liệu JSON không hợp lệ."})
                    continue

                msg_type = payload.get('type')
                data = payload.get('data', {})

                if msg_type == MSG_JOIN:
                    username = data.get('username')
                    req_room = data.get('room', session.room_code)
                    req_token = data.get('token', token)
                    await hub.handle_join(session, username, room_code=req_room, token=req_token)

                elif msg_type == MSG_MSG:
                    content = data.get('content')
                    await hub.handle_chat_message(session, content)

                elif msg_type == MSG_PRIVATE:
                    target_user = data.get('to')
                    content = data.get('content')
                    await hub.handle_private_message(session, target_user, content)

                elif msg_type == MSG_QUIT:
                    await hub.remove_client(session, reason="Client chủ động thoát")
                    break

                elif msg_type == 'MEDIA_STATE':
                    # Cập nhật trạng thái Mic/Cam/Screen/Hand và phát cho cùng phòng
                    media_data = data.get('state', {})
                    session.media_state = media_data
                    broadcast_payload = {
                        "client_id": session.id,
                        "username": session.username,
                        "media_state": media_data,
                        "room": session.room_code
                    }
                    await hub.broadcast('MEDIA_STATE', broadcast_payload, exclude_id=session.id, room_code=session.room_code)

                elif msg_type == 'SIGNAL':
                    # WebRTC signaling (offer, answer, candidate) chuyển tiếp giữa các peer trong phòng
                    to_id = data.get('to_id')
                    to_user = data.get('to_user')
                    signal_type = data.get('signal_type')
                    signal_payload = {
                        "from_id": session.id,
                        "from_user": session.username,
                        "from_fullname": session.fullname or session.username,
                        "signal": data.get('signal'),
                        "signal_type": signal_type,
                        "is_screen": data.get('is_screen', False),
                        "room": session.room_code
                    }
                    target_session = None
                    if to_id is not None:
                        try:
                            target_session = hub.clients.get(int(to_id))
                        except (ValueError, TypeError):
                            target_session = hub.clients.get(to_id)
                    if not target_session and to_user:
                        for s in hub.clients.values():
                            if s.is_active and s.username == to_user and getattr(s, 'room_code', '') == session.room_code:
                                target_session = s
                                break
                    if target_session and target_session.is_active:
                        hub.log(f"📡 [SIGNAL] {signal_type} từ #{session.id} ({session.username}) -> #{target_session.id} ({target_session.username})", tag='SIGNAL')
                        await hub.send_to_session(target_session, 'SIGNAL', signal_payload)
                    else:
                        hub.log(f"⚠️ [SIGNAL FAIL] Không tìm thấy người nhận #{to_id} ({to_user}) trong phòng {session.room_code}", tag='WARN')

                elif msg_type == 'REACTION':
                    # Biểu cảm emoji Google Meet (💖, 👍, 🎉, 👏, 😂, 😮)
                    emoji = data.get('emoji', '👍')
                    react_payload = {
                        "client_id": session.id,
                        "username": session.username,
                        "emoji": emoji,
                        "room": session.room_code
                    }
                    await hub.broadcast('REACTION', react_payload, room_code=session.room_code)

                elif msg_type == 'HOST_ACTION':
                    # Thao tác quản trị của Host (Mute all, khóa chat, etc.)
                    action = data.get('action')
                    if session.is_host or getattr(session, 'role', '') in ['admin', 'host']:
                        if action == 'mute_all':
                            await hub.host_mute_all(session.room_code)
                        elif action == 'toggle_public_chat':
                            enable = data.get('enable', True)
                            hub.host_toggle_chat(session.room_code, enable)
                            status_txt = "mở lại" if enable else "khóa"
                            await hub.broadcast(MSG_SYSTEM, {
                                "message": f"🔒 Host đã {status_txt} tính năng trò chuyện trong cuộc gọi."
                            }, room_code=session.room_code)

                elif msg_type == 'PING':
                    await ws.send_str(json.dumps({"type": "PONG", "data": {"timestamp": time.time()}}))

            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break

    except asyncio.CancelledError:
        pass
    except Exception as e:
        hub.log(f"Lỗi phiên WebSocket Client #{session.id}: {e}", tag='ERROR')
    finally:
        await hub.remove_client(session, reason="Ngắt kết nối WebSocket")

    return ws


async def websocket_admin_handler(request):
    """Xử lý kết nối WebSocket từ trang Admin Dashboard."""
    hub = request.app['hub']
    ws = web.WebSocketResponse(heartbeat=25.0)
    await ws.prepare(request)

    room_code = request.query.get('room', '').strip().lower()
    ws.room_code = room_code

    hub.admin_websockets.add(ws)
    hub.log(f"🖥️ Quản trị viên (Host) kết nối Host Studio [{room_code or 'Tất cả'}]", tag='SYSTEM')

    # Lọc danh sách client theo room_code nếu có
    if room_code:
        filtered_clients = [c.to_dict() for c in hub.clients.values() if getattr(c, 'room_code', '') == room_code]
    else:
        filtered_clients = [c.to_dict() for c in hub.clients.values()]

    # Gửi ngay gói tin khởi tạo toàn diện
    init_data = {
        "event": "INIT",
        "data": {
            "stats": hub.get_stats(),
            "clients": filtered_clients,
            "logs": hub.logs[-200:],
            "room_code": room_code
        }
    }
    await ws.send_str(json.dumps(init_data, ensure_ascii=False))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    command = json.loads(msg.data)
                    cmd_type = command.get('type')
                    cmd_data = command.get('data', {})

                    if cmd_type == 'ADMIN_KICK':
                        cid = int(cmd_data.get('client_id', -1))
                        reason = cmd_data.get('reason', 'Quản trị viên ngắt kết nối.')
                        ok, text = await hub.admin_kick(cid, reason)
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_BROADCAST':
                        text_msg = cmd_data.get('message', '')
                        ok, text = await hub.admin_broadcast(text_msg)
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_DM':
                        cid = int(cmd_data.get('client_id', -1))
                        text_msg = cmd_data.get('message', '')
                        ok, text = await hub.admin_direct_message(cid, text_msg)
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_TOGGLE_LOCK':
                        ok, text = await hub.admin_toggle_lock()
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_TOGGLE_PUBLIC_CHAT':
                        ok, text = await hub.admin_toggle_public_chat()
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_TOGGLE_PRIVATE_CHAT':
                        ok, text = await hub.admin_toggle_private_chat()
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_TOGGLE_MUTE':
                        cid = int(cmd_data.get('client_id', -1))
                        ok, text = await hub.admin_toggle_mute_client(cid)
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_MUTE_ALL':
                        ok, text = await hub.admin_mute_all()
                        await ws.send_str(json.dumps({"event": "ACTION_RESULT", "data": {"ok": ok, "message": text}}))

                    elif cmd_type == 'ADMIN_CLEAR_LOGS':
                        hub.logs.clear()
                        await hub._notify_admins('LOGS_CLEARED', {})

                except Exception as e:
                    await ws.send_str(json.dumps({"event": "ERROR", "data": {"message": str(e)}}))

    except Exception:
        pass
    finally:
        hub.admin_websockets.discard(ws)

    return ws


# ─────────────────────────────────────────────────────────────────
# HANDLERS GIAO THỨC TCP TRUYỀN THỐNG (PORT 9000)
# ─────────────────────────────────────────────────────────────────

async def tcp_client_handler(reader, writer, hub):
    """Xử lý kết nối từ các Client Desktop chạy Socket TCP truyền thống."""
    client_address = writer.get_extra_info('peername')
    session = await hub.register_client(
        client_type='tcp',
        address=client_address,
        reader=reader,
        writer=writer
    )

    buffer = ""

    try:
        while session.is_active:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break

            session.bytes_received += len(data)
            hub.total_bytes_transferred += len(data)

            try:
                text_chunk = data.decode(ENCODING)
            except UnicodeDecodeError:
                continue

            buffer += text_chunk

            # Xử lý các dòng kết thúc bằng '\n' theo quy chuẩn JSON-Lines
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue

                msg = parse_message(line)
                if not msg:
                    continue

                msg_type = msg.get('type')
                msg_data = msg.get('data', {})

                if msg_type == MSG_JOIN:
                    username = msg_data.get('username')
                    await hub.handle_join(session, username)

                elif msg_type == MSG_MSG:
                    content = msg_data.get('content')
                    await hub.handle_chat_message(session, content)

                elif msg_type == MSG_PRIVATE:
                    target_user = msg_data.get('to')
                    content = msg_data.get('content')
                    await hub.handle_private_message(session, target_user, content)

                elif msg_type == MSG_QUIT:
                    await hub.remove_client(session, reason="Client TCP chủ động QUIT")
                    return

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        hub.log(f"Lỗi Socket TCP Client #{session.id}: {e}", tag='ERROR')
    finally:
        await hub.remove_client(session, reason="Ngắt kết nối Socket TCP")


# ─────────────────────────────────────────────────────────────────
# API VÀ PHỤC VỤ WEB TĨNH (HTTP)
# ─────────────────────────────────────────────────────────────────

# REST APIs: Thống Kê & Danh Sách
async def api_stats_handler(request):
    hub = request.app['hub']
    return web.json_response(hub.get_stats())


async def api_clients_handler(request):
    hub = request.app['hub']
    room_code = request.query.get('room', '').strip().lower()
    if room_code:
        clients = [c.to_dict() for c in hub.clients.values() if getattr(c, 'room_code', '') == room_code]
    else:
        clients = [c.to_dict() for c in hub.clients.values()]
    return web.json_response(clients)


# REST APIs: Xác Thực Người Dùng (Zoom Style Auth)
async def api_auth_register_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "message": "Dữ liệu JSON không hợp lệ!"}, status=400)

    username = data.get('username', '')
    password = data.get('password', '')
    fullname = data.get('fullname', '')
    email = data.get('email', '')

    result = auth_manager.register(username, password, fullname, email)
    return web.json_response(result)


async def api_auth_login_handler(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "message": "Dữ liệu JSON không hợp lệ!"}, status=400)

    username = data.get('username', '')
    password = data.get('password', '')

    result = auth_manager.login(username, password)
    return web.json_response(result)


async def api_auth_logout_handler(request):
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip()
    if not token:
        try:
            data = await request.json()
            token = data.get('token', '')
        except Exception:
            pass

    result = auth_manager.logout(token)
    return web.json_response(result)


async def api_auth_me_handler(request):
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip() or request.query.get('token', '')
    user = auth_manager.get_user_by_token(token)
    if user:
        return web.json_response({"authenticated": True, "user": user})
    return web.json_response({"authenticated": False, "user": None})


# REST APIs: Quản Lý Đa Phòng Họp (Google Meet Style Rooms)
async def api_rooms_list_handler(request):
    """Lấy danh sách các cuộc họp đang diễn ra."""
    return web.json_response(room_manager.list_active_rooms())


async def api_rooms_create_handler(request):
    """Tạo phòng họp trực tuyến mới."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '').strip() or data.get('token', '')
    user = auth_manager.get_user_by_token(token)

    host_uname = user['username'] if user else data.get('host_username', 'guest_host')
    host_fname = user['fullname'] if user else data.get('host_fullname', 'Chủ Trì Cuộc Họp')

    title = data.get('title', '')
    custom_code = data.get('custom_code', None)

    room = room_manager.create_room(
        title=title,
        host_username=host_uname,
        host_fullname=host_fname,
        custom_code=custom_code
    )

    return web.json_response({
        "success": True,
        "room": room.to_dict(),
        "join_url": f"/room?code={room.code}",
        "admin_url": f"/admin?room={room.code}"
    })


async def api_rooms_get_handler(request):
    code = request.match_info.get('code', '').strip().lower()
    room = room_manager.get_room(code)
    if not room:
        return web.json_response({"success": False, "message": f"Phòng họp '{code}' không tồn tại!"}, status=404)
    return web.json_response({"success": True, "room": room.to_dict()})


# HTML Page Handlers
async def home_handler(request):
    """Phục vụ trang chủ Google Meet & Zoom Home Lobby."""
    home_path = os.path.join(BASE_DIR, 'web', 'home.html')
    if not os.path.exists(home_path):
        home_path = os.path.join(BASE_DIR, 'web', 'index.html')
    return web.FileResponse(
        home_path,
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
    )


async def room_handler(request):
    """Phục vụ phòng họp trực tuyến (Client Meeting Room)."""
    room_path = os.path.join(BASE_DIR, 'web', 'room.html')
    if not os.path.exists(room_path):
        room_path = os.path.join(BASE_DIR, 'web', 'index.html')
    return web.FileResponse(
        room_path,
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
    )


async def admin_page_handler(request):
    """Phục vụ trang web Host Studio riêng biệt (Google Meet / Zoom Host Control Center)."""
    admin_path = os.path.join(BASE_DIR, 'web', 'admin.html')
    if os.path.exists(admin_path):
        return web.FileResponse(
            admin_path,
            headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
        )
    return web.Response(text="Admin page not found. Please ensure 'web/admin.html' exists.", status=404)


def create_web_application(hub):
    """Khởi tạo ứng dụng aiohttp web."""
    @web.middleware
    async def no_cache_middleware(request, handler):
        response = await handler(request)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    app = web.Application(middlewares=[no_cache_middleware])
    app['hub'] = hub

    # Routes WebSocket
    app.router.add_get('/ws', websocket_client_handler)
    app.router.add_get('/ws/admin', websocket_admin_handler)

    # REST APIs: Auth (Zoom Style)
    app.router.add_post('/api/auth/register', api_auth_register_handler)
    app.router.add_post('/api/auth/login', api_auth_login_handler)
    app.router.add_post('/api/auth/logout', api_auth_logout_handler)
    app.router.add_get('/api/auth/me', api_auth_me_handler)

    # REST APIs: Rooms (Google Meet Style)
    app.router.add_get('/api/rooms', api_rooms_list_handler)
    app.router.add_post('/api/rooms/create', api_rooms_create_handler)
    app.router.add_get('/api/rooms/{code}', api_rooms_get_handler)

    # REST APIs: Stats & Clients
    app.router.add_get('/api/stats', api_stats_handler)
    app.router.add_get('/api/clients', api_clients_handler)

    # HTML Pages
    app.router.add_get('/', home_handler)
    app.router.add_get('/home', home_handler)
    app.router.add_get('/home.html', home_handler)
    app.router.add_get('/room', room_handler)
    app.router.add_get('/room.html', room_handler)
    app.router.add_get('/admin', admin_page_handler)
    app.router.add_get('/admin.html', admin_page_handler)

    # Phục vụ tài nguyên tĩnh (css, js, assets)
    web_dir = os.path.join(BASE_DIR, 'web')
    if os.path.exists(web_dir):
        app.router.add_static('/', path=web_dir, name='static', show_index=False)

    return app


async def start_dual_server(host=HOST, web_port=WEB_PORT, tcp_port=TCP_PORT):
    """
    Khởi động song song cả Máy chủ Web (HTTP+WS) và Máy chủ TCP Socket.
    """
    hub = DualChatHub()

    # 1. Khởi động Web Server (aiohttp)
    app = create_web_application(hub)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, web_port)
    try:
        await site.start()
    except OSError as e:
        await runner.cleanup()
        if e.errno in (98, 48, 10048):  # EADDRINUSE on Linux / macOS / Windows
            print(f"\n❌ [LỖI KHỞI ĐỘNG] Cổng Web {web_port} đang bị chiếm dụng bởi một tiến trình khác!")
            print(f"👉 Gợi ý: Hãy tắt tiến trình đang chạy cổng {web_port} (ví dụ: fuser -k {web_port}/tcp hoặc kill PID)")
        else:
            print(f"\n❌ [LỖI KHỞI ĐỘNG] Không thể lắng nghe cổng Web {web_port}: {e}")
        return

    hub.log(f"🚀 [WEB SERVER] Khởi chạy thành công tại http://{host}:{web_port}", tag='SUCCESS')

    # 2. Khởi động TCP Socket Server (asyncio)
    async def _tcp_cb(reader, writer):
        await tcp_client_handler(reader, writer, hub)

    try:
        tcp_server = await asyncio.start_server(_tcp_cb, host, tcp_port)
    except OSError as e:
        await runner.cleanup()
        if e.errno in (98, 48, 10048):
            print(f"\n❌ [LỖI KHỞI ĐỘNG] Cổng TCP Socket {tcp_port} đang bị chiếm dụng bởi một tiến trình khác!")
            print(f"👉 Gợi ý: Hãy tắt tiến trình đang chạy cổng {tcp_port} (ví dụ: fuser -k {tcp_port}/tcp)")
        else:
            print(f"\n❌ [LỖI KHỞI ĐỘNG] Không thể lắng nghe cổng TCP {tcp_port}: {e}")
        return

    hub.log(f"🔌 [TCP SERVER] Đang lắng nghe Socket tại {host}:{tcp_port}", tag='SUCCESS')
    hub.log(f"✨ Hỗ trợ đồng thời Web Client (Browser) & Desktop Client (Tkinter)", tag='SUCCESS')

    # Giữ server chạy vĩnh viễn
    try:
        async with tcp_server:
            await tcp_server.serve_forever()
    finally:
        await runner.cleanup()


def run_standalone():
    """Hàm chạy độc lập từ console."""
    try:
        asyncio.run(start_dual_server())
    except KeyboardInterrupt:
        print("\n[SERVER] Đã nhận tín hiệu dừng. Đóng máy chủ an toàn.")


if __name__ == '__main__':
    run_standalone()
