"""
Quản Lý Đa Phòng Họp Trực Tuyến (Multi-Room Meeting Manager)
Phong cách Google Meet & Zoom: Sinh mã phòng ngẫu nhiên dạng abc-defg-hij,
cách ly tin nhắn và người tham gia theo từng phòng riêng biệt.
"""

import string
import secrets
from datetime import datetime

def generate_meet_code() -> str:
    """Sinh mã cuộc họp ngẫu nhiên chuẩn phong cách Google Meet: abc-defg-hij."""
    letters = string.ascii_lowercase
    part1 = ''.join(secrets.choice(letters) for _ in range(3))
    part2 = ''.join(secrets.choice(letters) for _ in range(4))
    part3 = ''.join(secrets.choice(letters) for _ in range(3))
    return f"{part1}-{part2}-{part3}"


class MeetingRoom:
    """Đại diện cho một phòng họp trực tuyến cụ thể."""

    def __init__(self, code: str, title: str, host_username: str, host_fullname: str = ""):
        self.code = code
        self.title = title or f"Cuộc họp {code}"
        self.host_username = host_username
        self.host_fullname = host_fullname or host_username
        self.created_at = datetime.now()
        self.is_locked = False
        self.allow_public_chat = True
        self.allow_private_chat = True
        self.clients = set()  # Tập hợp các ClientSession đang kết nối trong phòng này
        self.chat_history = []
        self.max_history = 100

    @property
    def online_count(self) -> int:
        return len([c for c in self.clients if getattr(c, 'is_active', True) and getattr(c, 'username', None)])

    def add_client(self, client):
        self.clients.add(client)
        client.room_code = self.code

    def remove_client(self, client):
        self.clients.discard(client)

    def add_chat(self, msg_data):
        self.chat_history.append(msg_data)
        if len(self.chat_history) > self.max_history:
            self.chat_history.pop(0)

    def to_dict(self):
        return {
            "code": self.code,
            "title": self.title,
            "host_username": self.host_username,
            "host_fullname": self.host_fullname,
            "created_at": self.created_at.strftime("%H:%M:%S"),
            "online_count": self.online_count,
            "is_locked": self.is_locked,
            "allow_public_chat": self.allow_public_chat,
            "allow_private_chat": self.allow_private_chat
        }


class RoomManager:
    """Trình quản lý tập trung toàn bộ các phòng họp trực tuyến trên hệ thống."""

    def __init__(self):
        self.rooms = {}  # code -> MeetingRoom
        self.seed_default_rooms()

    def seed_default_rooms(self):
        """Tạo phòng mặc định cho các kết nối tổng và ứng dụng Desktop."""
        default_room = MeetingRoom(
            code="seminar-network-lab",
            title="Phòng Hội Thảo Seminar Lập Trình Mạng",
            host_username="admin",
            host_fullname="Ban Quản Trị Seminar"
        )
        self.rooms[default_room.code] = default_room

    def create_room(self, title: str, host_username: str, host_fullname: str = "", custom_code: str = None) -> MeetingRoom:
        """Tạo một phòng họp mới."""
        if custom_code:
            code = custom_code.strip().lower()
        else:
            # Sinh mã ngẫu nhiên đến khi không trùng lặp
            while True:
                code = generate_meet_code()
                if code not in self.rooms:
                    break

        room = MeetingRoom(
            code=code,
            title=title or f"Cuộc họp {code}",
            host_username=host_username,
            host_fullname=host_fullname
        )
        self.rooms[code] = room
        return room

    def get_room(self, code: str) -> MeetingRoom:
        if not code:
            return self.rooms.get("seminar-network-lab")
        code = code.strip().lower()
        return self.rooms.get(code)

    def get_or_create_room(self, code: str, title: str = "", host: str = "guest") -> MeetingRoom:
        room = self.get_room(code)
        if not room:
            room = self.create_room(title=title, host_username=host, custom_code=code)
        return room

    def delete_room(self, code: str) -> bool:
        """Hủy/ngắt một phòng họp khỏi hệ thống."""
        if not code:
            return False
        code = code.strip().lower()
        if code in self.rooms:
            del self.rooms[code]
            return True
        return False

    def list_active_rooms(self):
        """Danh sách các cuộc họp đang diễn ra hoặc phòng vừa được khởi tạo."""
        now = datetime.now()
        # Chỉ dọn dẹp các phòng tạm quá 2 giờ không có người tham gia
        expired_rooms = [
            code for code, r in self.rooms.items()
            if code != 'seminar-network-lab' and r.online_count == 0 and (now - r.created_at).total_seconds() > 7200
        ]
        for c in expired_rooms:
            del self.rooms[c]

        # Trả về các phòng có người online hoặc phòng mới được tạo trong ngày
        return [r.to_dict() for r in self.rooms.values()]


# Singleton instance
room_manager = RoomManager()
