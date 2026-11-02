"""
Hệ Thống Xác Thực Người Dùng (Authentication System)
Hỗ trợ Đăng ký, Đăng nhập, Quản lý Token Session theo phong cách Zoom / Google Meet.
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'netsphere.db')

AVATAR_COLORS = [
    "#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#14B8A6", "#3B82F6", "#6366F1"
]

class AuthManager:
    """Quản lý tài khoản người dùng và phiên làm việc (Session Tokens)."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.sessions = {}  # token -> {username, fullname, email, avatar_color, created_at}
        self.init_db()
        self.seed_default_accounts()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    fullname TEXT NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    avatar_color TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

    def seed_default_accounts(self):
        """Khởi tạo một số tài khoản mặc định phục vụ chạy thử và thuyết trình Seminar."""
        default_users = [
            ("admin", "Admin Quản Trị", "admin@seminar.edu.vn", "admin123", "#EF4444", "admin"),
            ("giangvien", "TS. Nguyễn Văn Hướng Dẫn", "teacher@seminar.edu.vn", "123456", "#4F46E5", "host"),
            ("sinhvien1", "Trần Minh Thắng (Báo Cáo)", "thang@student.edu.vn", "123456", "#10B981", "user")
        ]
        with self.get_connection() as conn:
            for uname, fname, email, pwd, color, role in default_users:
                cur = conn.cursor()
                cur.execute("SELECT username FROM users WHERE username = ?", (uname,))
                if not cur.fetchone():
                    salt = secrets.token_hex(8)
                    pwd_hash = self.hash_password(pwd, salt)
                    cur.execute('''
                        INSERT INTO users (username, fullname, email, password_hash, salt, avatar_color, role)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (uname, fname, email, pwd_hash, salt, color, role))
            conn.commit()

    def register(self, username: str, password: str, fullname: str, email: str = ""):
        """Đăng ký tài khoản người dùng mới."""
        username = username.strip().lower()
        fullname = fullname.strip() or username
        email = email.strip()

        if not username or len(username) < 3:
            return {"success": False, "message": "Tên đăng nhập phải có ít nhất 3 ký tự!"}
        if not password or len(password) < 4:
            return {"success": False, "message": "Mật khẩu phải có ít nhất 4 ký tự!"}

        color = secrets.choice(AVATAR_COLORS)
        salt = secrets.token_hex(8)
        pwd_hash = self.hash_password(password, salt)

        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO users (username, fullname, email, password_hash, salt, avatar_color)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, fullname, email, pwd_hash, salt, color))
                conn.commit()
            
            # Tự động cấp token đăng nhập sau khi đăng ký thành công
            token = secrets.token_hex(24)
            user_info = {
                "username": username,
                "fullname": fullname,
                "email": email,
                "avatar_color": color,
                "role": "user"
            }
            self.sessions[token] = user_info
            return {"success": True, "token": token, "user": user_info, "message": "Đăng ký tài khoản thành công!"}

        except sqlite3.IntegrityError:
            return {"success": False, "message": "Tên đăng nhập đã được sử dụng. Vui lòng chọn tên khác!"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi hệ thống: {str(e)}"}

    def login(self, username: str, password: str):
        """Xác thực đăng nhập người dùng."""
        username = username.strip().lower()
        if not username or not password:
            return {"success": False, "message": "Vui lòng nhập tên đăng nhập và mật khẩu!"}

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, fullname, email, password_hash, salt, avatar_color, role FROM users WHERE username = ?", (username,))
            row = cur.fetchone()

        if not row:
            return {"success": False, "message": "Tài khoản không tồn tại trên hệ thống!"}

        salt = row['salt']
        expected_hash = row['password_hash']
        if self.hash_password(password, salt) != expected_hash:
            return {"success": False, "message": "Mật khẩu không chính xác!"}

        token = secrets.token_hex(24)
        user_info = {
            "username": row['username'],
            "fullname": row['fullname'],
            "email": row['email'],
            "avatar_color": row['avatar_color'],
            "role": row['role']
        }
        self.sessions[token] = user_info
        return {"success": True, "token": token, "user": user_info, "message": "Đăng nhập thành công!"}

    def get_user_by_token(self, token: str):
        """Lấy thông tin người dùng từ Session Token."""
        if not token:
            return None
        return self.sessions.get(token)

    def logout(self, token: str):
        """Hủy phiên đăng nhập."""
        if token in self.sessions:
            del self.sessions[token]
            return {"success": True, "message": "Đã đăng xuất thành công!"}
        return {"success": True, "message": "Phiên làm việc đã kết thúc."}

# Khởi tạo singleton auth_manager
auth_manager = AuthManager()
