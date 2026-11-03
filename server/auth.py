"""
Hệ Thống Xác Thực & Quản Lý Dữ Liệu Người Dùng (Authentication & Database System)
Hỗ trợ PostgreSQL (pgAdmin4) với cơ chế tự động chuyển đổi và dự phòng SQLite.
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import DictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SQLITE_DB_PATH = os.path.join(DATA_DIR, 'netsphere.db')

AVATAR_COLORS = [
    "#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#14B8A6", "#3B82F6", "#6366F1"
]

class AuthManager:
    """Quản lý tài khoản người dùng và phiên làm việc kết nối PostgreSQL / SQLite."""

    def __init__(self):
        self.sqlite_path = SQLITE_DB_PATH
        self.sessions = {}  # token -> {username, fullname, email, avatar_color, created_at}
        self.engine = 'sqlite'
        self.db_name = getattr(config, 'DB_NAME', 'seminar_meet_db')

        # Thử kết nối PostgreSQL (pgAdmin4) trước nếu được cấu hình
        if getattr(config, 'DB_ENGINE', 'postgresql') == 'postgresql' and HAS_PSYCOPG2:
            try:
                self._test_and_setup_postgres()
                self.engine = 'postgresql'
                print(f"[AUTH] 🐘 Đã kết nối cơ sở dữ liệu PostgreSQL (pgAdmin4): {self.db_name}@{config.DB_HOST}:{config.DB_PORT}")
            except Exception as e:
                print(f"[AUTH] ⚠️ Không thể kết nối PostgreSQL ({e}). Tự động chuyển sang SQLite dự phòng.")
                self.engine = 'sqlite'
        else:
            self.engine = 'sqlite'

        if self.engine == 'sqlite':
            print(f"[AUTH] 📁 Đang sử dụng cơ sở dữ liệu SQLite: {self.sqlite_path}")

        self.init_db()
        self.seed_default_accounts()

    def _test_and_setup_postgres(self):
        """Kiểm tra và tự động tạo database trong PostgreSQL nếu chưa tồn tại."""
        # Kết nối tới database mặc định postgres để kiểm tra database dự án
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dbname='postgres'
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{self.db_name}";')
            print(f"[AUTH] ✨ Đã tạo mới cơ sở dữ liệu '{self.db_name}' trên PostgreSQL.")
        conn.close()

    def get_connection(self):
        """Khởi tạo kết nối cơ sở dữ liệu theo engine hiện hành."""
        if self.engine == 'postgresql':
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                dbname=self.db_name
            )
            return conn
        else:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            return conn

    def _get_cursor(self, conn):
        """Trả về cursor trả dữ liệu kiểu dict cho cả 2 engine."""
        if self.engine == 'postgresql':
            return conn.cursor(cursor_factory=DictCursor)
        else:
            return conn.cursor()

    def _format_query(self, query: str) -> str:
        """Chuẩn hóa cú pháp tham số giữa PostgreSQL (%s) và SQLite (?)."""
        if self.engine == 'sqlite':
            return query.replace('%s', '?')
        return query

    def init_db(self):
        """Khởi tạo cấu trúc các bảng dữ liệu."""
        with self.get_connection() as conn:
            cur = self._get_cursor(conn)
            if self.engine == 'postgresql':
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        username VARCHAR(50) PRIMARY KEY,
                        fullname VARCHAR(100) NOT NULL,
                        email VARCHAR(100),
                        password_hash VARCHAR(128) NOT NULL,
                        salt VARCHAR(32) NOT NULL,
                        avatar_color VARCHAR(16) NOT NULL,
                        role VARCHAR(20) DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS meeting_rooms (
                        room_code VARCHAR(50) PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        host_username VARCHAR(50),
                        is_locked BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id SERIAL PRIMARY KEY,
                        room_code VARCHAR(50),
                        sender_username VARCHAR(50) NOT NULL,
                        sender_fullname VARCHAR(100),
                        recipient_username VARCHAR(50),
                        message_type VARCHAR(20) DEFAULT 'text',
                        content TEXT,
                        file_url TEXT,
                        file_name VARCHAR(255),
                        file_size INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
            else:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        fullname TEXT NOT NULL,
                        email TEXT,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        avatar_color TEXT NOT NULL,
                        role TEXT DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                ''')
            conn.commit()

    def hash_password(self, password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

    def seed_default_accounts(self):
        """Khởi tạo tài khoản mẫu và sao chép người dùng có sẵn."""
        default_users = [
            ("admin", "Admin Quản Trị", "admin@seminar.edu.vn", "admin123", "#EF4444", "admin"),
            ("giangvien", "TS. Nguyễn Văn Hướng Dẫn", "teacher@seminar.edu.vn", "123456", "#4F46E5", "host"),
            ("sinhvien1", "Trần Minh Thắng (Báo Cáo)", "thang@student.edu.vn", "123456", "#10B981", "user")
        ]
        with self.get_connection() as conn:
            cur = self._get_cursor(conn)
            for uname, fname, email, pwd, color, role in default_users:
                cur.execute(self._format_query("SELECT username FROM users WHERE username = %s"), (uname,))
                if not cur.fetchone():
                    salt = secrets.token_hex(8)
                    pwd_hash = self.hash_password(pwd, salt)
                    cur.execute(self._format_query('''
                        INSERT INTO users (username, fullname, email, password_hash, salt, avatar_color, role)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    '''), (uname, fname, email, pwd_hash, salt, color, role))
            conn.commit()

    def register(self, username: str, password: str, fullname: str, email: str = ""):
        """Đăng ký tài khoản người dùng mới trực tiếp vào PostgreSQL / SQLite."""
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

        integrity_errors = (sqlite3.IntegrityError,)
        if HAS_PSYCOPG2:
            integrity_errors = (sqlite3.IntegrityError, psycopg2.IntegrityError)

        try:
            with self.get_connection() as conn:
                cur = self._get_cursor(conn)
                cur.execute(self._format_query('''
                    INSERT INTO users (username, fullname, email, password_hash, salt, avatar_color)
                    VALUES (%s, %s, %s, %s, %s, %s)
                '''), (username, fullname, email, pwd_hash, salt, color))
                conn.commit()

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

        except integrity_errors:
            return {"success": False, "message": "Tên đăng nhập đã được sử dụng. Vui lòng chọn tên khác!"}
        except Exception as e:
            return {"success": False, "message": f"Lỗi cơ sở dữ liệu: {str(e)}"}

    def login(self, username: str, password: str):
        """Xác thực đăng nhập người dùng từ PostgreSQL / SQLite."""
        username = username.strip().lower()
        if not username or not password:
            return {"success": False, "message": "Vui lòng nhập tên đăng nhập và mật khẩu!"}

        try:
            with self.get_connection() as conn:
                cur = self._get_cursor(conn)
                cur.execute(self._format_query('''
                    SELECT username, fullname, email, password_hash, salt, avatar_color, role 
                    FROM users WHERE username = %s
                '''), (username,))
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
        except Exception as e:
            return {"success": False, "message": f"Lỗi kết nối cơ sở dữ liệu: {str(e)}"}

    def get_user_by_token(self, token: str):
        """Lấy thông tin người dùng từ Session Token."""
        if not token:
            return None
        return self.sessions.get(token)

    def logout(self, token: str):
        """Hủy phiên làm việc."""
        if token in self.sessions:
            del self.sessions[token]
            return {"success": True, "message": "Đã đăng xuất thành công!"}
        return {"success": True, "message": "Phiên làm việc đã kết thúc."}

# Khởi tạo singleton auth_manager
auth_manager = AuthManager()
