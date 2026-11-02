import socket
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from config import HOST, PORT, BUFFER_SIZE
from common.protocol import (
    MSG_JOIN, MSG_MSG, MSG_PRIVATE, MSG_QUIT,
    MSG_WELCOME, MSG_SYSTEM, MSG_ERROR, MSG_ONLINE_LIST,
    encode_message, decode_messages
)


class ChatGUI:
    """
    Ứng dụng Chat Client giao diện đồ họa Tkinter.
    """

    # Hằng số lựa chọn người nhận chat
    CHAT_ALL = "Tất cả mọi người (Phòng chung)"

    # Bảng màu giao diện hiện đại (Modern Theme)
    COLOR_PRIMARY = "#4F46E5"      # Indigo chủ đạo
    COLOR_PRIMARY_HOVER = "#4338CA"
    COLOR_BG = "#F8FAFC"           # Xám nhạt nền
    COLOR_CARD = "#FFFFFF"         # Trắng khối thẻ
    COLOR_TEXT = "#1E293B"         # Đen xám chữ chính
    COLOR_MUTED = "#64748B"        # Xám chữ phụ / thời gian
    COLOR_BORDER = "#E2E8F0"       # Viền
    COLOR_SUCCESS = "#10B981"      # Xanh lá trạng thái
    COLOR_SYSTEM = "#D97706"       # Vàng cam hệ thống
    COLOR_PRIVATE = "#9333EA"      # Tím tin nhắn riêng
    COLOR_SELF = "#2563EB"         # Xanh dương tin nhắn của mình

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TCP Chat - Seminar Lập Trình Mạng")
        self.root.geometry("900x640")
        self.root.minsize(760, 520)
        self.root.configure(bg=self.COLOR_BG)

        # Cấu hình icon nếu có, hoặc thiết lập xử lý đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Socket & Network State
        self.client_socket = None
        self.connected = False
        self.username = ""
        self.online_users = []
        self.recv_thread = None
        self.msg_queue = queue.Queue()

        # Cấu hình kiểu dáng ttk
        self._setup_styles()

        # Tạo container chứa các màn hình
        self.container = tk.Frame(self.root, bg=self.COLOR_BG)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Tạo 2 màn hình chính: Màn hình Đăng nhập & Màn hình Chat
        self.login_frame = None
        self.chat_frame = None

        self.show_login_screen()


    def _setup_styles(self):
        """Khởi tạo các định dạng ttk cho nút bấm, ô nhập."""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 10), background=self.COLOR_BG)

        # Nút bấm chính (Primary Button)
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.COLOR_PRIMARY,
            foreground="#FFFFFF",
            padding=(12, 7),
            borderwidth=0
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.COLOR_PRIMARY_HOVER), ("pressed", "#3730A3")]
        )

        # Nút phụ (Secondary/Danger)
        style.configure(
            "Danger.TButton",
            font=("Segoe UI", 9),
            background="#EF4444",
            foreground="#FFFFFF",
            padding=(10, 5),
            borderwidth=0
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#DC2626")]
        )

        # Entry
        style.configure(
            "Custom.TEntry",
            padding=6,
            relief="flat"
        )

    def show_login_screen(self):
        """Hiển thị màn hình cấu hình kết nối và nhập tên người dùng."""
        if self.chat_frame:
            self.chat_frame.destroy()
            self.chat_frame = None

        self.login_frame = tk.Frame(self.container, bg=self.COLOR_BG)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        # Card trung tâm
        card = tk.Frame(
            self.login_frame,
            bg=self.COLOR_CARD,
            bd=1,
            relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER,
            highlightthickness=1,
            padx=40,
            pady=35
        )
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Tiêu đề
        lbl_badge = tk.Label(
            card,
            text="SEMINAR LẬP TRÌNH SOCKET TCP/IP",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_PRIMARY,
            bg=self.COLOR_CARD
        )
        lbl_badge.pack(anchor=tk.W, pady=(0, 4))

        lbl_title = tk.Label(
            card,
            text="Tham Gia Phòng Chat",
            font=("Segoe UI", 18, "bold"),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        )
        lbl_title.pack(anchor=tk.W, pady=(0, 6))

        lbl_desc = tk.Label(
            card,
            text="Kết nối máy khách tới máy chủ TCP Chat Server",
            font=("Segoe UI", 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        )
        lbl_desc.pack(anchor=tk.W, pady=(0, 20))

        # Form fields
        form = tk.Frame(card, bg=self.COLOR_CARD)
        form.pack(fill=tk.X, pady=5)

        # IP Server
        tk.Label(
            form, text="Địa chỉ Server (IP):", font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).grid(row=0, column=0, sticky=tk.W, pady=(6, 2))
        self.entry_host = ttk.Entry(form, width=32, style="Custom.TEntry")
        default_host = '127.0.0.1' if HOST == '0.0.0.0' else HOST
        self.entry_host.insert(0, default_host)
        self.entry_host.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))

        # Port
        tk.Label(
            form, text="Cổng kết nối (Port):", font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).grid(row=2, column=0, sticky=tk.W, pady=(6, 2))
        self.entry_port = ttk.Entry(form, width=32, style="Custom.TEntry")
        self.entry_port.insert(0, str(PORT))
        self.entry_port.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))

        # Username
        tk.Label(
            form, text="Tên của bạn (Username):", font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).grid(row=4, column=0, sticky=tk.W, pady=(6, 2))
        self.entry_username = ttk.Entry(form, width=32, style="Custom.TEntry")
        self.entry_username.grid(row=5, column=0, sticky=tk.W, pady=(0, 15))
        self.entry_username.focus_set()

        # Nhấn Enter để kết nối
        self.entry_username.bind("<Return>", lambda e: self.action_connect())

        # Thông báo lỗi (nếu có)
        self.lbl_login_msg = tk.Label(
            card, text="", font=("Segoe UI", 9),
            fg="#DC2626", bg=self.COLOR_CARD
        )
        self.lbl_login_msg.pack(fill=tk.X, pady=(0, 10))

        # Nút Kết nối
        btn_connect = ttk.Button(
            card,
            text="🚀 Kết Nối & Vào Phòng",
            style="Primary.TButton",
            command=self.action_connect
        )
        btn_connect.pack(fill=tk.X, pady=(5, 0))

    def show_chat_screen(self):
        """Hiển thị giao diện phòng chat sau khi kết nối thành công."""
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None

        self.chat_frame = tk.Frame(self.container, bg=self.COLOR_BG)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)

        # ─── 1. THANH TIÊU ĐỀ TRÊN CÙNG (HEADER) ───
        header = tk.Frame(self.chat_frame, bg=self.COLOR_CARD, height=56, padx=16, pady=10)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Logo / Tên phòng
        header_left = tk.Frame(header, bg=self.COLOR_CARD)
        header_left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(
            header_left,
            text="💬 PHÒNG CHAT TCP/IP",
            font=("Segoe UI", 12, "bold"),
            fg=self.COLOR_PRIMARY,
            bg=self.COLOR_CARD
        ).pack(side=tk.LEFT)

        self.lbl_status = tk.Label(
            header_left,
            text=f"  ● Đang kết nối tới {self.host}:{self.port}",
            font=("Segoe UI", 9),
            fg=self.COLOR_SUCCESS,
            bg=self.COLOR_CARD
        )
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # Thông tin người dùng & Nút thoát
        header_right = tk.Frame(header, bg=self.COLOR_CARD)
        header_right.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(
            header_right,
            text=f"👤 Bạn: {self.username}",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        ).pack(side=tk.LEFT, padx=(0, 14))

        btn_disconnect = ttk.Button(
            header_right,
            text="Rời phòng",
            style="Danger.TButton",
            command=self.action_disconnect
        )
        btn_disconnect.pack(side=tk.LEFT)

        # Đường kẻ phân cách
        sep = tk.Frame(self.chat_frame, height=1, bg=self.COLOR_BORDER)
        sep.pack(fill=tk.X, side=tk.TOP)

        # ─── 2. KHU VỰC TRUNG TÂM (CHAT LOG & USER LIST) ───
        middle_container = tk.Frame(self.chat_frame, bg=self.COLOR_BG)
        middle_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 6))

        # --- Khung Chat Chính (Bên Trái) ---
        chat_box_frame = tk.Frame(middle_container, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID, highlightbackground=self.COLOR_BORDER)
        chat_box_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.chat_area = scrolledtext.ScrolledText(
            chat_box_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
            relief=tk.FLAT,
            padx=12,
            pady=12,
            state=tk.DISABLED
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # Định nghĩa các tags style cho văn bản chat
        self._configure_chat_tags()

        # --- Khung Danh Sách Người Dùng (Bên Phải) ---
        user_panel = tk.Frame(middle_container, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID, highlightbackground=self.COLOR_BORDER, width=220)
        user_panel.pack(side=tk.RIGHT, fill=tk.Y)
        user_panel.pack_propagate(False)

        # Tiêu đề danh sách online
        user_panel_header = tk.Frame(user_panel, bg=self.COLOR_CARD, padx=10, pady=8)
        user_panel_header.pack(fill=tk.X)

        self.lbl_online_count = tk.Label(
            user_panel_header,
            text="👥 Đang Online (0)",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        )
        self.lbl_online_count.pack(anchor=tk.W)

        tk.Label(
            user_panel,
            text="Nhấp đúp chuột để gửi tin riêng",
            font=("Segoe UI", 8),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        ).pack(anchor=tk.W, padx=10, pady=(0, 6))

        # Listbox người dùng
        list_container = tk.Frame(user_panel, bg=self.COLOR_CARD)
        list_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        user_scrollbar = tk.Scrollbar(list_container)
        user_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.user_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg=self.COLOR_TEXT,
            selectbackground=self.COLOR_PRIMARY,
            selectforeground="#FFFFFF",
            relief=tk.FLAT,
            activestyle='none',
            yscrollcommand=user_scrollbar.set
        )
        self.user_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        user_scrollbar.config(command=self.user_listbox.yview)
 
        # Bắt sự kiện double-click vào người dùng để chat riêng
        self.user_listbox.bind("<Double-Button-1>", self.on_user_double_click)

        # ─── 3. KHU VỰC NHẬP TIN NHẮN (BOTTOM TOOLBAR) ───
        bottom_frame = tk.Frame(self.chat_frame, bg=self.COLOR_CARD, padx=14, pady=10, bd=1, relief=tk.SOLID, highlightbackground=self.COLOR_BORDER)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=14, pady=(0, 10))

        # Hàng 1: Chọn đối tượng nhận + Emoji Toolbar
        toolbar_row = tk.Frame(bottom_frame, bg=self.COLOR_CARD)
        toolbar_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            toolbar_row,
            text="Gửi tới:",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.recipient_var = tk.StringVar(value=self.CHAT_ALL)
        self.recipient_combo = ttk.Combobox(
            toolbar_row,
            textvariable=self.recipient_var,
            state="readonly",
            width=26
        )
        self.recipient_combo['values'] = [self.CHAT_ALL]
        self.recipient_combo.pack(side=tk.LEFT, padx=(0, 15))

        # Thanh Emoji nhanh
        tk.Label(
            toolbar_row,
            text="Emoji nhanh:",
            font=("Segoe UI", 9),
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        ).pack(side=tk.LEFT, padx=(0, 4))

        quick_emojis = ["😊", "😂", "❤️", "👍", "🎉", "🔥", "👋", "🚀", "💻", "🎯"]
        emoji_frame = tk.Frame(toolbar_row, bg=self.COLOR_CARD)
        emoji_frame.pack(side=tk.LEFT)

        for emo in quick_emojis:
            btn_emo = tk.Button(
                emoji_frame,
                text=emo,
                font=("Segoe UI Emoji", 9),
                bg=self.COLOR_CARD,
                fg=self.COLOR_TEXT,
                activebackground="#EEF2FF",
                relief=tk.FLAT,
                bd=0,
                padx=3,
                pady=1,
                cursor="hand2",
                command=lambda e=emo: self.insert_emoji(e)
            )
            btn_emo.pack(side=tk.LEFT, padx=1)

        # Hàng 2: Ô nhập văn bản và nút gửi
        input_row = tk.Frame(bottom_frame, bg=self.COLOR_CARD)
        input_row.pack(fill=tk.X)

        self.msg_entry = ttk.Entry(
            input_row,
            font=("Segoe UI", 10),
            style="Custom.TEntry"
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda e: self.action_send_message())
        self.msg_entry.focus_set()

        btn_send = ttk.Button(
            input_row,
            text="Gửi ➤",
            style="Primary.TButton",
            command=self.action_send_message
        )
        btn_send.pack(side=tk.RIGHT)

    def _configure_chat_tags(self):
        """Cấu hình các tag màu sắc cho hiển thị tin nhắn trong ScrolledText."""
        # Thời gian
        self.chat_area.tag_configure("time", foreground=self.COLOR_MUTED, font=("Segoe UI", 8))

        # Người gửi
        self.chat_area.tag_configure("self_name", foreground=self.COLOR_SELF, font=("Segoe UI", 9, "bold"))
        self.chat_area.tag_configure("other_name", foreground="#059669", font=("Segoe UI", 9, "bold"))
        self.chat_area.tag_configure("pm_name", foreground=self.COLOR_PRIVATE, font=("Segoe UI", 9, "bold"))

        # Nội dung
        self.chat_area.tag_configure("msg_text", foreground=self.COLOR_TEXT, font=("Segoe UI", 10))
        self.chat_area.tag_configure("pm_text", foreground="#701A75", font=("Segoe UI", 10))

        # Hệ thống / Thông báo
        self.chat_area.tag_configure(
            "system",
            foreground=self.COLOR_SYSTEM,
            font=("Segoe UI", 9, "italic")
        )

        # Lỗi
        self.chat_area.tag_configure("error", foreground="#DC2626", font=("Segoe UI", 9, "bold"))

        # Huy hiệu (Badge)
        self.chat_area.tag_configure(
            "badge_pm",
            foreground="#FFFFFF",
            background=self.COLOR_PRIVATE,
            font=("Segoe UI", 8, "bold")
        )

    def insert_emoji(self, emoji_char):
        """Chèn biểu tượng cảm xúc vào ô nhập tin nhắn."""
        if hasattr(self, 'msg_entry') and self.msg_entry:
            self.msg_entry.insert(tk.INSERT, emoji_char)
            self.msg_entry.focus_set()

    def on_user_double_click(self, event):
        """Khi nhấp đúp vào một người trong danh sách online, chuyển sang chat riêng."""
        selection = self.user_listbox.curselection()
        if not selection:
            return

        selected_user = self.user_listbox.get(selection[0])
        # Loại bỏ ký tự đánh dấu nếu có
        selected_user = selected_user.replace("👤 ", "").replace(" (Bạn)", "").strip()

        if selected_user == self.username:
            messagebox.showinfo("Thông báo", "Bạn không thể gửi tin nhắn riêng cho chính mình.")
            return

        # Đặt người nhận trong Combobox
        self.recipient_var.set(selected_user)
        self.msg_entry.focus_set()

    def append_chat(self, segments):
        self.chat_area.config(state=tk.NORMAL)
        for text, tag in segments:
            if tag:
                self.chat_area.insert(tk.END, text, tag)
            else:
                self.chat_area.insert(tk.END, text)
        self.chat_area.insert(tk.END, "\n")
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def refresh_user_list_ui(self, users):
        self.online_users = users

        # Cập nhật nhãn số lượng
        self.lbl_online_count.config(text=f"👥 Đang Online ({len(users)})")

        # Cập nhật Listbox
        self.user_listbox.delete(0, tk.END)
        for u in users:
            display_name = f"👤 {u}"
            if u == self.username:
                display_name += " (Bạn)"
            self.user_listbox.insert(tk.END, display_name)

        # Cập nhật Combobox người nhận (loại trừ chính mình)
        other_users = [u for u in users if u != self.username]
        new_values = [self.CHAT_ALL] + other_users
        self.recipient_combo['values'] = new_values

        # Nếu người nhận hiện tại không còn online nữa, reset về Chat All
        current_recipient = self.recipient_var.get()
        if current_recipient != self.CHAT_ALL and current_recipient not in other_users:
            self.recipient_var.set(self.CHAT_ALL)

    def action_connect(self):
        """Xử lý kết nối tới TCP Chat Server."""
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()
        username = self.entry_username.get().strip()

        # Validate dữ liệu
        if not host:
            self.lbl_login_msg.config(text="Vui lòng nhập địa chỉ Server (Host).")
            return

        try:
            port = int(port_str)
            if not (1024 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.lbl_login_msg.config(text="Port phải là số nguyên trong khoảng 1024 - 65535.")
            return

        if not username:
            self.lbl_login_msg.config(text="Vui lòng nhập tên người dùng (Username).")
            return

        self.host = host
        self.port = port
        self.username = username
        self.lbl_login_msg.config(text="Đang kết nối tới máy chủ...", fg=self.COLOR_PRIMARY)

        # Tạo socket TCP và kết nối
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))

            # Gửi gói JOIN
            join_msg = encode_message(MSG_JOIN, {"username": self.username})
            self.client_socket.sendall(join_msg)

            # Chờ phản hồi ban đầu từ Server
            raw_response = self.client_socket.recv(BUFFER_SIZE)
            if not raw_response:
                raise ConnectionError("Server đóng kết nối ngay sau khi gửi JOIN.")

            messages = decode_messages(raw_response)
            if not messages:
                raise ValueError("Không nhận được phản hồi hợp lệ từ Server.")

            first_msg = messages[0]
            if first_msg['type'] == MSG_ERROR:
                error_desc = first_msg['data'].get('message', 'Không thể tham gia.')
                self.lbl_login_msg.config(text=f"Lỗi: {error_desc}", fg="#DC2626")
                self.client_socket.close()
                return

            if first_msg['type'] != MSG_WELCOME:
                self.lbl_login_msg.config(text="Phản hồi không mong muốn từ Server.", fg="#DC2626")
                self.client_socket.close()
                return

            # Kết nối thành công!
            self.connected = True
            welcome_text = first_msg['data'].get('message', '')

            # Chuyển sang màn hình chat
            self.show_chat_screen()

            # Hiển thị thông điệp chào mừng
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.append_chat([
                (f"[{timestamp}] ", "time"),
                (f"🎉 {welcome_text}", "system")
            ])

            # Nếu trong đợt recv đầu tiên có kèm các tin khác (ví dụ: ONLINE_LIST)
            for subsequent_msg in messages[1:]:
                self.handle_incoming_message(subsequent_msg)

            # Khởi động Network Thread để liên tục lắng nghe tin nhắn
            self.recv_thread = threading.Thread(
                target=self._network_receive_loop,
                daemon=True
            )
            self.recv_thread.start()

            # Bắt đầu vòng lặp đọc hàng đợi tin nhắn trên Main Thread
            self.root.after(50, self._process_queue)

        except ConnectionRefusedError:
            self.lbl_login_msg.config(
                text=f"Không thể kết nối tới {self.host}:{self.port}. Server chưa chạy!",
                fg="#DC2626"
            )
            if self.client_socket:
                self.client_socket.close()
        except Exception as e:
            self.lbl_login_msg.config(text=f"Lỗi kết nối: {e}", fg="#DC2626")
            if self.client_socket:
                self.client_socket.close()

    def _process_queue(self):
        if not self.connected:
            return

        try:
            while not self.msg_queue.empty():
                item = self.msg_queue.get_nowait()
                if item == "__DISCONNECTED__":
                    self.handle_server_disconnected()
                    return
                else:
                    self.handle_incoming_message(item)
        except queue.Empty:
            pass

        if self.connected:
            self.root.after(50, self._process_queue)

    def _network_receive_loop(self):
        while self.connected:
            try:
                raw_data = self.client_socket.recv(BUFFER_SIZE)
                if not raw_data:
                    break

                messages = decode_messages(raw_data)
                for msg in messages:
                    self.msg_queue.put(msg)

            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
            except Exception:
                break

        # Khi kết thúc vòng lặp -> Báo ngắt kết nối vào queue
        if self.connected:
            self.msg_queue.put("__DISCONNECTED__")

    def handle_incoming_message(self, msg):
        """
        Xử lý từng tin nhắn nhận được (chạy trên Main Thread).
        """
        msg_type = msg.get('type')
        data = msg.get('data', {})

        if msg_type == MSG_MSG:
            # ── Tin nhắn chat chung ──
            sender = data.get('username', '???')
            content = data.get('content', '')
            timestamp = data.get('timestamp', datetime.now().strftime("%H:%M:%S"))

            is_me = (sender == self.username)
            sender_tag = "self_name" if is_me else "other_name"
            sender_display = f"{sender} (Bạn)" if is_me else sender

            self.append_chat([
                (f"[{timestamp}] ", "time"),
                (f"{sender_display}: ", sender_tag),
                (content, "msg_text")
            ])

        elif msg_type == MSG_PRIVATE:
            # ── Tin nhắn chat riêng ──
            from_user = data.get('from', '???')
            to_user = data.get('to', '???')
            content = data.get('content', '')
            timestamp = data.get('timestamp', datetime.now().strftime("%H:%M:%S"))
            is_sender = data.get('is_sender', False)

            if is_sender:
                # Mình gửi cho người khác
                self.append_chat([
                    (f"[{timestamp}] ", "time"),
                    (" 🔒 TIN RIÊNG ", "badge_pm"),
                    (f" Tới {to_user}: ", "pm_name"),
                    (content, "pm_text")
                ])
            else:
                # Người khác gửi cho mình
                self.append_chat([
                    (f"[{timestamp}] ", "time"),
                    (" 🔒 TIN RIÊNG ", "badge_pm"),
                    (f" Từ {from_user}: ", "pm_name"),
                    (content, "pm_text")
                ])

        elif msg_type == MSG_ONLINE_LIST:
            # ── Cập nhật danh sách online ──
            users = data.get('users', [])
            self.refresh_user_list_ui(users)

        elif msg_type == MSG_SYSTEM:
            # ── Thông báo hệ thống ──
            sys_msg = data.get('message', '')
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.append_chat([
                (f"[{timestamp}] ", "time"),
                (f"📢 {sys_msg}", "system")
            ])

        elif msg_type == MSG_ERROR:
            # ── Thông báo lỗi từ Server ──
            err_msg = data.get('message', '')
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.append_chat([
                (f"[{timestamp}] ", "time"),
                (f"❌ Lỗi: {err_msg}", "error")
            ])

    def action_send_message(self):
        """Xử lý gửi tin nhắn (chat chung hoặc chat riêng)."""
        if not self.connected or not self.client_socket:
            return

        content = self.msg_entry.get().strip()
        if not content:
            return

        recipient = self.recipient_var.get()

        try:
            if recipient == self.CHAT_ALL:
                # Gửi chat chung tới cả phòng
                msg = encode_message(MSG_MSG, {"content": content})
                self.client_socket.sendall(msg)
            else:
                # Gửi tin nhắn riêng (Private Message)
                msg = encode_message(MSG_PRIVATE, {
                    "to": recipient,
                    "content": content
                })
                self.client_socket.sendall(msg)

            # Xóa ô nhập tin nhắn và đặt lại tiêu điểm
            self.msg_entry.delete(0, tk.END)
            self.msg_entry.focus_set()

        except OSError as e:
            messagebox.showerror("Lỗi mạng", f"Không thể gửi tin nhắn: {e}")
            self.action_disconnect()

    def handle_server_disconnected(self):
        """Xử lý khi máy chủ ngắt kết nối đột ngột."""
        self.connected = False
        messagebox.showwarning(
        )
        self.show_login_screen()

    def action_disconnect(self):
        """Người dùng chủ động nhấn 'Rời phòng'."""
        if self.connected and self.client_socket:
            try:
                quit_msg = encode_message(MSG_QUIT, {})
                self.client_socket.sendall(quit_msg)
            except OSError:
                pass
            finally:
                self.connected = False
                try:
                    self.client_socket.close()
                except OSError:
                    pass

        self.show_login_screen()

    def on_closing(self):
        """Xử lý khi đóng cửa sổ ứng dụng."""
        if self.connected and self.client_socket:
            try:
                quit_msg = encode_message(MSG_QUIT, {})
                self.client_socket.sendall(quit_msg)
            except OSError:
                pass
            finally:
                self.connected = False
                try:
                    self.client_socket.close()
                except OSError:
                    pass

        self.root.destroy()

    def run(self):
        """Chạy vòng lặp giao diện Tkinter."""
        self.root.mainloop()