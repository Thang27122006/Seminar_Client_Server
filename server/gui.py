import os
import sys
import queue
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

from config import HOST, PORT
from server.server import ChatServer


class ServerGUI:
    COLOR_HEADER_BG = "#0F172A"       # Xanh đen Slate 900 sang trọng
    COLOR_HEADER_TEXT = "#F8FAFC"     # Chữ trắng tiêu đề
    COLOR_PAGE_BG = "#F1F5F9"         # Nền xám nhạt dịu mắt
    COLOR_CARD = "#FFFFFF"            # Trắng khối thẻ
    COLOR_BORDER = "#E2E8F0"          # Viền thẻ
    COLOR_TEXT = "#0F172A"            # Chữ đen chính
    COLOR_MUTED = "#64748B"           # Chữ phụ / chú thích
    COLOR_PRIMARY = "#4F46E5"         # Tím xanh Indigo
    COLOR_PRIMARY_HOVER = "#4338CA"
    COLOR_SUCCESS = "#10B981"         # Xanh lục thành công / Online
    COLOR_DANGER = "#EF4444"          # Đỏ nguy hiểm / Kick / Dừng
    COLOR_DANGER_HOVER = "#DC2626"
    COLOR_WARNING = "#F59E0B"         # Vàng cam cảnh báo
    COLOR_INFO = "#0284C7"            # Xanh dương thông tin
    COLOR_PURPLE = "#8B5CF6"          # Tím cho tin nhắn riêng

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🖥️ TCP Chat Server Controller - Giám Sát & Quản Lý Client ID")
        self.root.geometry("1140x740")
        self.root.minsize(980, 640)
        self.root.configure(bg=self.COLOR_PAGE_BG)

        # Xử lý sự kiện đóng cửa sổ an toàn
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Server State
        self.server = None
        self.is_running = False
        self.start_time = None
        self.event_queue = queue.Queue()

        # Dữ liệu quản lý Client trên GUI (mapping: client_id -> dict)
        self.client_records = {}
        self.selected_client_id = None

        # Thiết lập kiểu dáng ttk
        self._setup_styles()

        # Xây dựng giao diện người dùng
        self._build_ui()

        # Bắt đầu vòng lặp xử lý sự kiện bất đồng bộ
        self.root.after(40, self._process_events)

        # Vòng lặp cập nhật thời gian hoạt động (Uptime)
        self.root.after(1000, self._update_uptime_tick)

    def run(self):
        """Khởi động vòng lặp giao diện Tkinter."""
        self.root.mainloop()

    def _setup_styles(self):
        """Định dạng các widget ttk cho thẩm mỹ hiện đại."""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 9), background=self.COLOR_PAGE_BG)

        # Nút Bấm Chính (Khởi Động / Thao Tác)
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background=self.COLOR_PRIMARY,
            foreground="#FFFFFF",
            padding=(12, 6),
            borderwidth=0
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.COLOR_PRIMARY_HOVER), ("pressed", "#3730A3")]
        )

        # Nút Bấm Khởi Động (Success Button)
        style.configure(
            "Success.TButton",
            font=("Segoe UI", 9, "bold"),
            background=self.COLOR_SUCCESS,
            foreground="#FFFFFF",
            padding=(12, 6),
            borderwidth=0
        )
        style.map(
            "Success.TButton",
            background=[("active", "#059669"), ("pressed", "#047857")]
        )

        # Nút Bấm Dừng / Ngắt Kết Nối (Danger Button)
        style.configure(
            "Danger.TButton",
            font=("Segoe UI", 9, "bold"),
            background=self.COLOR_DANGER,
            foreground="#FFFFFF",
            padding=(10, 6),
            borderwidth=0
        )
        style.map(
            "Danger.TButton",
            background=[("active", self.COLOR_DANGER_HOVER), ("pressed", "#B91C1C")]
        )

        # Nút Bấm Phụ (Secondary Button)
        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#E2E8F0",
            foreground=self.COLOR_TEXT,
            padding=(10, 5),
            borderwidth=0
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#CBD5E1")]
        )

        # Ô Nhập Dữ Liệu
        style.configure(
            "Custom.TEntry",
            padding=5,
            relief="flat"
        )

        # Bảng Danh Sách Client (Treeview)
        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=self.COLOR_TEXT,
            rowheight=28,
            fieldbackground="#FFFFFF",
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#F8FAFC",
            foreground=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"),
            padding=(6, 6)
        )
        style.map(
            "Treeview",
            background=[("selected", "#EEF2FF")],
            foreground=[("selected", self.COLOR_PRIMARY)]
        )

    def _build_ui(self):
        """Xây dựng toàn bộ cây giao diện của Server Dashboard."""
        # 1. THANH TIÊU ĐỀ TRÊN CÙNG (DARK HEADER)
        self._build_header()

        # 2. KHỐI THẺ THỐNG KÊ & ĐIỀU KHIỂN (METRIC & CONTROL CARDS)
        self._build_top_cards()

        # 3. KHU VỰC TRUNG TÂM (CHIA ĐÔI: BẢNG CLIENT ID BÊN TRÁI, LOGS & BROADCAST BÊN PHẢI)
        self._build_center_panes()

        # 4. THANH TRẠNG THÁI CUỐI TRANG (STATUS BAR)
        self._build_status_bar()

    def _build_header(self):
        """Thanh Header mang nhận diện chuyên nghiệp của Quản trị máy chủ."""
        header = tk.Frame(self.root, bg=self.COLOR_HEADER_BG, height=60, padx=20, pady=10)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # Góc trái: Tiêu đề & Giới thiệu
        title_box = tk.Frame(header, bg=self.COLOR_HEADER_BG)
        title_box.pack(side=tk.LEFT, fill=tk.Y)

        lbl_icon_title = tk.Label(
            title_box,
            text="🖥️  TCP CHAT SERVER CONTROLLER",
            font=("Segoe UI", 12, "bold"),
            fg=self.COLOR_HEADER_TEXT,
            bg=self.COLOR_HEADER_BG
        )
        lbl_icon_title.pack(anchor=tk.W)

        lbl_sub = tk.Label(
            title_box,
            text="Hệ Thống Quản Lý Kết Nối & Giám Sát Client ID • Seminar Lập Trình Mạng",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg=self.COLOR_HEADER_BG
        )
        lbl_sub.pack(anchor=tk.W)

        # Góc phải: Huy hiệu trạng thái & Bộ đếm thời gian
        right_box = tk.Frame(header, bg=self.COLOR_HEADER_BG)
        right_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_server_status_badge = tk.Label(
            right_box,
            text="● ĐÃ DỪNG (STOPPED)",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#EF4444",
            padx=12,
            pady=4,
            relief=tk.FLAT
        )
        self.lbl_server_status_badge.pack(side=tk.LEFT, padx=10)

        self.lbl_uptime = tk.Label(
            right_box,
            text="⏱️ Uptime: 00:00:00",
            font=("Segoe UI", 9, "bold"),
            fg="#E2E8F0",
            bg=self.COLOR_HEADER_BG
        )
        self.lbl_uptime.pack(side=tk.LEFT)

    def _build_top_cards(self):
        """Khối điều khiển Server nhanh và các chỉ số KPI hoạt động."""
        container = tk.Frame(self.root, bg=self.COLOR_PAGE_BG, padx=16, pady=12)
        container.pack(fill=tk.X, side=tk.TOP)

        # Chia thành lưới 4 cột (Điều khiển | Online | Tổng Phiên | Tổng Tin nhắn)
        container.columnconfigure(0, weight=4)
        container.columnconfigure(1, weight=2)
        container.columnconfigure(2, weight=2)
        container.columnconfigure(3, weight=2)

        # --- Thẻ 1: Điều Khiển Khởi Động / Dừng Máy Chủ ---
        card_ctrl = tk.Frame(
            container, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=10
        )
        card_ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        lbl_ctrl_title = tk.Label(
            card_ctrl, text="⚙️ CẤU HÌNH & KHỞI ĐỘNG MÁY CHỦ",
            font=("Segoe UI", 9, "bold"), fg=self.COLOR_PRIMARY, bg=self.COLOR_CARD
        )
        lbl_ctrl_title.pack(anchor=tk.W, pady=(0, 6))

        cfg_row = tk.Frame(card_ctrl, bg=self.COLOR_CARD)
        cfg_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(cfg_row, text="IP:", font=("Segoe UI", 9, "bold"), fg=self.COLOR_TEXT, bg=self.COLOR_CARD).pack(side=tk.LEFT)
        self.entry_host = ttk.Entry(cfg_row, width=14, style="Custom.TEntry")
        self.entry_host.insert(0, HOST)
        self.entry_host.pack(side=tk.LEFT, padx=(4, 10))

        tk.Label(cfg_row, text="Port:", font=("Segoe UI", 9, "bold"), fg=self.COLOR_TEXT, bg=self.COLOR_CARD).pack(side=tk.LEFT)
        self.entry_port = ttk.Entry(cfg_row, width=7, style="Custom.TEntry")
        self.entry_port.insert(0, str(PORT))
        self.entry_port.pack(side=tk.LEFT, padx=(4, 10))

        # Phím chọn nhanh IP (LAN / 127.0.0.1 / 0.0.0.0)
        btn_preset_local = tk.Button(
            cfg_row, text="Localhost", font=("Segoe UI", 8),
            bg="#F1F5F9", fg=self.COLOR_TEXT, relief=tk.FLAT, padx=5, pady=1,
            command=lambda: self._set_host("127.0.0.1")
        )
        btn_preset_local.pack(side=tk.LEFT, padx=2)

        btn_preset_all = tk.Button(
            cfg_row, text="0.0.0.0", font=("Segoe UI", 8),
            bg="#F1F5F9", fg=self.COLOR_TEXT, relief=tk.FLAT, padx=5, pady=1,
            command=lambda: self._set_host("0.0.0.0")
        )
        btn_preset_all.pack(side=tk.LEFT, padx=2)

        # Nút Bật / Tắt Server
        self.btn_toggle_server = ttk.Button(
            card_ctrl,
            text="▶ Khởi Động Server",
            style="Success.TButton",
            command=self.action_toggle_server
        )
        self.btn_toggle_server.pack(fill=tk.X, pady=(4, 0))

        # --- Thẻ 2: Số Client Online ---
        card_online = self._create_metric_card(
            container, col=1, title="CLIENTS ONLINE",
            default_val="0", label="Đang kết nối", color=self.COLOR_SUCCESS, icon="👥"
        )
        self.lbl_val_online = card_online

        # --- Thẻ 3: Tổng Lượt Kết Nối (Sessions) ---
        card_total = self._create_metric_card(
            container, col=2, title="TỔNG KẾT NỐI",
            default_val="0", label="Lượt Client đã vào", color=self.COLOR_PRIMARY, icon="📈"
        )
        self.lbl_val_total_conns = card_total

        # --- Thẻ 4: Tổng Tin Nhắn Gửi Nhận ---
        card_msgs = self._create_metric_card(
            container, col=3, title="TỔNG TIN NHẮN",
            default_val="0", label="Gói tin trung chuyển", color=self.COLOR_INFO, icon="💬"
        )
        self.lbl_val_total_msgs = card_msgs

    def _create_metric_card(self, parent, col, title, default_val, label, color, icon):
        """Hàm tiện ích tạo thẻ chỉ số đẹp mắt."""
        card = tk.Frame(
            parent, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=10
        )
        card.grid(row=0, column=col, sticky="nsew", padx=(0, 10 if col < 3 else 0))

        top_row = tk.Frame(card, bg=self.COLOR_CARD)
        top_row.pack(fill=tk.X)

        tk.Label(
            top_row, text=f"{icon} {title}", font=("Segoe UI", 8, "bold"),
            fg=self.COLOR_MUTED, bg=self.COLOR_CARD
        ).pack(side=tk.LEFT)

        val_label = tk.Label(
            card, text=default_val, font=("Segoe UI", 22, "bold"),
            fg=color, bg=self.COLOR_CARD
        )
        val_label.pack(anchor=tk.W, pady=(2, 0))

        tk.Label(
            card, text=label, font=("Segoe UI", 8),
            fg=self.COLOR_MUTED, bg=self.COLOR_CARD
        ).pack(anchor=tk.W)

        return val_label

    def _set_host(self, host_val):
        """Cập nhật giá trị ô nhập Host."""
        if not self.is_running:
            self.entry_host.delete(0, tk.END)
            self.entry_host.insert(0, host_val)

    def _build_center_panes(self):
        center_frame = tk.Frame(self.root, bg=self.COLOR_PAGE_BG, padx=16, pady=0)
        center_frame.pack(fill=tk.BOTH, expand=True)

        self.paned = ttk.PanedWindow(center_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # ─── BÊN TRÁI: QUẢN LÝ CLIENT & HIỂN THỊ CLIENT ID ───
        left_card = tk.Frame(
            self.paned, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=12
        )
        self.paned.add(left_card, weight=3)

        # Header bảng Client
        left_header = tk.Frame(left_card, bg=self.COLOR_CARD)
        left_header.pack(fill=tk.X, pady=(0, 8))

        lbl_client_section = tk.Label(
            left_header,
            text="👥 DANH SÁCH CLIENTS KẾT NỐI (HIỂN THỊ CLIENT ID)",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        )
        lbl_client_section.pack(side=tk.LEFT)

        # Ô tìm kiếm / lọc Client
        search_box = tk.Frame(left_header, bg=self.COLOR_CARD)
        search_box.pack(side=tk.RIGHT)

        tk.Label(search_box, text="🔍", font=("Segoe UI", 9), bg=self.COLOR_CARD).pack(side=tk.LEFT)
        self.entry_search_client = ttk.Entry(search_box, width=16, style="Custom.TEntry")
        self.entry_search_client.pack(side=tk.LEFT, padx=(2, 0))
        self.entry_search_client.bind("<KeyRelease>", lambda e: self._filter_client_tree())

        # Bảng Treeview hiển thị Client ID và các thông số
        tree_frame = tk.Frame(left_card, bg=self.COLOR_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        columns = ("id", "username", "address", "fileno", "connected_at", "status", "msg_count")
        self.client_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Định dạng tiêu đề và độ rộng từng cột
        self.client_tree.heading("id", text="Client ID", anchor=tk.CENTER)
        self.client_tree.heading("username", text="Username", anchor=tk.W)
        self.client_tree.heading("address", text="Địa chỉ IP : Port", anchor=tk.W)
        self.client_tree.heading("fileno", text="Socket FD", anchor=tk.CENTER)
        self.client_tree.heading("connected_at", text="Giờ vào", anchor=tk.CENTER)
        self.client_tree.heading("status", text="Trạng thái", anchor=tk.CENTER)
        self.client_tree.heading("msg_count", text="Số tin", anchor=tk.CENTER)

        self.client_tree.column("id", width=85, minwidth=75, anchor=tk.CENTER)
        self.client_tree.column("username", width=120, minwidth=90, anchor=tk.W)
        self.client_tree.column("address", width=145, minwidth=110, anchor=tk.W)
        self.client_tree.column("fileno", width=75, minwidth=60, anchor=tk.CENTER)
        self.client_tree.column("connected_at", width=75, minwidth=65, anchor=tk.CENTER)
        self.client_tree.column("status", width=95, minwidth=80, anchor=tk.CENTER)
        self.client_tree.column("msg_count", width=60, minwidth=50, anchor=tk.CENTER)

        # Scrollbars cho Treeview
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.client_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.client_tree.xview)
        self.client_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.client_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Gắn thẻ màu cho các trạng thái trong bảng
        self.client_tree.tag_configure("online", background="#ECFDF5", foreground="#065F46")
        self.client_tree.tag_configure("pending", background="#FFFBEB", foreground="#92400E")
        self.client_tree.tag_configure("disconnected", background="#F8FAFC", foreground="#94A3B8")

        # Bắt sự kiện chọn dòng trên bảng
        self.client_tree.bind("<<TreeviewSelect>>", self._on_client_selected)

        # Thanh thao tác Client được chọn (Kick, Gửi PM, Copy)
        action_bar = tk.Frame(left_card, bg="#F8FAFC", bd=1, relief=tk.SOLID, padx=10, pady=8)
        action_bar.pack(fill=tk.X, pady=(8, 0))

        self.lbl_selected_info = tk.Label(
            action_bar,
            text="👉 Hãy chọn một Client từ bảng để thao tác",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_MUTED,
            bg="#F8FAFC"
        )
        self.lbl_selected_info.pack(anchor=tk.W, pady=(0, 6))

        btn_row = tk.Frame(action_bar, bg="#F8FAFC")
        btn_row.pack(fill=tk.X)

        self.btn_kick = ttk.Button(
            btn_row,
            text="🚫 Kick (Ngắt kết nối)",
            style="Danger.TButton",
            command=self.action_kick_selected,
            state=tk.DISABLED
        )
        self.btn_kick.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_pm = ttk.Button(
            btn_row,
            text="✉️ Gửi Tin Riêng (PM)",
            style="Primary.TButton",
            command=self.action_pm_selected,
            state=tk.DISABLED
        )
        self.btn_pm.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_copy_info = ttk.Button(
            btn_row,
            text="📋 Copy ID & IP",
            style="Secondary.TButton",
            command=self.action_copy_client_info,
            state=tk.DISABLED
        )
        self.btn_copy_info.pack(side=tk.LEFT, padx=(0, 6))

        # ─── BÊN PHẢI: NHẬT KÝ HOẠT ĐỘNG & PHÁT THÔNG BÁO HỆ THỐNG ───
        right_card = tk.Frame(
            self.paned, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=12
        )
        self.paned.add(right_card, weight=3)

        # Header Nhật ký
        right_header = tk.Frame(right_card, bg=self.COLOR_CARD)
        right_header.pack(fill=tk.X, pady=(0, 8))

        lbl_log_title = tk.Label(
            right_header,
            text="📜 NHẬT KÝ MÁY CHỦ THỜI GIAN THỰC",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        )
        lbl_log_title.pack(side=tk.LEFT)

        # Bộ lọc nhật ký và các nút tiện ích
        log_tools = tk.Frame(right_header, bg=self.COLOR_CARD)
        log_tools.pack(side=tk.RIGHT)

        self.auto_scroll_var = tk.BooleanVar(value=True)
        chk_scroll = tk.Checkbutton(
            log_tools, text="Tự cuộn", variable=self.auto_scroll_var,
            font=("Segoe UI", 8), bg=self.COLOR_CARD, activebackground=self.COLOR_CARD
        )
        chk_scroll.pack(side=tk.LEFT, padx=(0, 8))

        btn_clear_log = ttk.Button(
            log_tools, text="🗑️ Xóa", style="Secondary.TButton",
            command=self.action_clear_log
        )
        btn_clear_log.pack(side=tk.LEFT, padx=(0, 4))

        btn_save_log = ttk.Button(
            log_tools, text="💾 Lưu file", style="Secondary.TButton",
            command=self.action_save_log
        )
        btn_save_log.pack(side=tk.LEFT)

        # Khung văn bản hiển thị Nhật ký với màu sắc phong phú
        self.txt_log = scrolledtext.ScrolledText(
            right_card,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#0F172A",
            fg="#E2E8F0",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=4)
        self._configure_log_tags()

        # KHUNG PHÁT THÔNG BÁO TỚI TẤT CẢ CLIENT (BROADCAST)
        broadcast_box = tk.Frame(right_card, bg="#F8FAFC", bd=1, relief=tk.SOLID, padx=10, pady=8)
        broadcast_box.pack(fill=tk.X, pady=(8, 0))

        tk.Label(
            broadcast_box,
            text="📢 PHÁT THÔNG BÁO TOÀN HỆ THỐNG (BROADCAST ANNOUNCEMENT):",
            font=("Segoe UI", 9, "bold"),
            fg=self.COLOR_PRIMARY,
            bg="#F8FAFC"
        ).pack(anchor=tk.W, pady=(0, 4))

        send_row = tk.Frame(broadcast_box, bg="#F8FAFC")
        send_row.pack(fill=tk.X)

        self.entry_broadcast = ttk.Entry(send_row, style="Custom.TEntry")
        self.entry_broadcast.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.entry_broadcast.bind("<Return>", lambda e: self.action_broadcast())

        self.btn_broadcast = ttk.Button(
            send_row,
            text="🚀 Gửi Tới Tất Cả",
            style="Primary.TButton",
            command=self.action_broadcast
        )
        self.btn_broadcast.pack(side=tk.RIGHT)

    def _configure_log_tags(self):
        """Cấu hình các thẻ định dạng màu sắc cho bảng nhật ký ScrolledText."""
        self.txt_log.tag_configure("TIME", foreground="#94A3B8")
        self.txt_log.tag_configure("INFO", foreground="#E2E8F0")
        self.txt_log.tag_configure("CONNECT", foreground="#60A5FA", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("JOIN", foreground="#34D399", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("CHAT", foreground="#F8FAFC")
        self.txt_log.tag_configure("PRIVATE", foreground="#C084FC", font=("Consolas", 9, "italic"))
        self.txt_log.tag_configure("LEAVE", foreground="#FBBF24")
        self.txt_log.tag_configure("SUCCESS", foreground="#4ADE80", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("WARNING", foreground="#F59E0B")
        self.txt_log.tag_configure("ERROR", foreground="#F87171", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("SYSTEM", foreground="#38BDF8", font=("Consolas", 9, "bold"))

    def _build_status_bar(self):
        """Thanh trạng thái chân trang."""
        status_bar = tk.Frame(self.root, bg="#E2E8F0", height=26, padx=14)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.lbl_status_msg = tk.Label(
            status_bar,
            text="🟢 Sẵn sàng khởi động máy chủ.",
            font=("Segoe UI", 8),
            fg=self.COLOR_TEXT,
            bg="#E2E8F0"
        )
        self.lbl_status_msg.pack(side=tk.LEFT)

        lbl_tech = tk.Label(
            status_bar,
            text="Socket TCP/IP • Multithreading • Python 3",
            font=("Segoe UI", 8),
            fg=self.COLOR_MUTED,
            bg="#E2E8F0"
        )
        lbl_tech.pack(side=tk.RIGHT)

    def _process_events(self):
        """Rút các sự kiện từ background threads và cập nhật lên UI chính."""
        try:
            while True:
                event_name, data = self.event_queue.get_nowait()

                if event_name == 'status':
                    is_active, host, port = data
                    self._handle_status_update(is_active, host, port)

                elif event_name == 'log':
                    timestamp, message, tag = data
                    self._append_log(timestamp, message, tag)

                elif event_name == 'client_connect':
                    self._handle_client_connect(data)

                elif event_name == 'client_join':
                    self._handle_client_join(data)

                elif event_name == 'client_update':
                    self._handle_client_update(data)

                elif event_name == 'client_leave':
                    self._handle_client_leave(data)

                elif event_name == 'message':
                    self._refresh_kpis()

        except queue.Empty:
            pass

        finally:
            self.root.after(40, self._process_events)

    def _update_uptime_tick(self):
        """Cập nhật đồng hồ đo thời gian chạy của Server mỗi giây."""
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            self.lbl_uptime.config(text=f"⏱️ Uptime: {hrs:02d}:{mins:02d}:{secs:02d}")
        else:
            self.lbl_uptime.config(text="⏱️ Uptime: 00:00:00")

        self.root.after(1000, self._update_uptime_tick)

    def _handle_client_connect(self, client_data):
        """Xử lý khi một Client vừa kết nối TCP (đã được cấp Client ID)."""
        cid = client_data['id']
        self.client_records[cid] = client_data

        # Thêm dòng mới vào Treeview
        display_id = f"#{cid:02d}" if cid < 100 else f"#{cid}"
        self.client_tree.insert(
            "",
            tk.END,
            iid=str(cid),
            values=(
                display_id,
                client_data['username'],
                client_data['address'],
                client_data['fileno'],
                client_data['connected_at'],
                client_data['status'],
                client_data['msg_count']
            ),
            tags=("pending",)
        )
        self._refresh_kpis()

    def _handle_client_join(self, client_data):
        """Xử lý khi Client đã gửi thành công lệnh JOIN (xác nhận username)."""
        cid = client_data['id']
        self.client_records[cid] = client_data

        display_id = f"#{cid:02d}" if cid < 100 else f"#{cid}"
        if self.client_tree.exists(str(cid)):
            self.client_tree.item(
                str(cid),
                values=(
                    display_id,
                    client_data['username'],
                    client_data['address'],
                    client_data['fileno'],
                    client_data['connected_at'],
                    client_data['status'],
                    client_data['msg_count']
                ),
                tags=("online",)
            )
        else:
            self.client_tree.insert(
                "",
                tk.END,
                iid=str(cid),
                values=(
                    display_id,
                    client_data['username'],
                    client_data['address'],
                    client_data['fileno'],
                    client_data['connected_at'],
                    client_data['status'],
                    client_data['msg_count']
                ),
                tags=("online",)
            )

        self._refresh_kpis()
        self._update_selected_action_bar()

    def _handle_client_update(self, client_data):
        """Cập nhật số tin nhắn hoặc thông tin của Client."""
        cid = client_data['id']
        self.client_records[cid] = client_data

        display_id = f"#{cid:02d}" if cid < 100 else f"#{cid}"
        if self.client_tree.exists(str(cid)):
            tag = "online" if client_data.get('is_active') else "disconnected"
            self.client_tree.item(
                str(cid),
                values=(
                    display_id,
                    client_data['username'],
                    client_data['address'],
                    client_data['fileno'],
                    client_data['connected_at'],
                    client_data['status'],
                    client_data['msg_count']
                ),
                tags=(tag,)
            )
        self._refresh_kpis()

    def _handle_client_leave(self, client_data):
        """Xử lý khi Client ngắt kết nối."""
        cid = client_data['id']
        self.client_records[cid] = client_data

        display_id = f"#{cid:02d}" if cid < 100 else f"#{cid}"
        if self.client_tree.exists(str(cid)):
            self.client_tree.item(
                str(cid),
                values=(
                    display_id,
                    client_data['username'],
                    client_data['address'],
                    client_data['fileno'],
                    client_data['connected_at'],
                    client_data['status'],
                    client_data['msg_count']
                ),
                tags=("disconnected",)
            )

        self._refresh_kpis()
        self._update_selected_action_bar()

    def _filter_client_tree(self):
        """Tìm kiếm lọc danh sách Client theo ID hoặc Username."""
        query = self.entry_search_client.get().strip().lower()

        for cid, data in self.client_records.items():
            iid = str(cid)
            if not self.client_tree.exists(iid):
                continue

            id_str = f"#{cid}".lower()
            name_str = (data.get('username') or "").lower()
            addr_str = (data.get('address') or "").lower()

            if not query or query in id_str or query in name_str or query in addr_str or query in str(cid):
                # Hiển thị lại nếu khớp
                self.client_tree.reattach(iid, "", tk.END)
            else:
                self.client_tree.detach(iid)

    def _on_client_selected(self, event):
        """Sự kiện click chọn một dòng Client trên Treeview."""
        selected = self.client_tree.selection()
        if not selected:
            self.selected_client_id = None
        else:
            try:
                self.selected_client_id = int(selected[0])
            except ValueError:
                self.selected_client_id = None

        self._update_selected_action_bar()

    def _update_selected_action_bar(self):
        """Cập nhật trạng thái các nút bấm thao tác dựa theo Client đang chọn."""
        if not self.selected_client_id or self.selected_client_id not in self.client_records:
            self.lbl_selected_info.config(
                text="👉 Hãy chọn một Client từ bảng để thao tác",
                fg=self.COLOR_MUTED
            )
            self.btn_kick.config(state=tk.DISABLED)
            self.btn_pm.config(state=tk.DISABLED)
            self.btn_copy_info.config(state=tk.DISABLED)
            return

        client = self.client_records[self.selected_client_id]
        cid = client['id']
        uname = client['username']
        addr = client['address']
        is_active = client.get('is_active', False)

        status_text = f"Đang chọn: Client ID #{cid} • '{uname}' ({addr})"
        self.lbl_selected_info.config(text=status_text, fg=self.COLOR_PRIMARY)

        # Cho phép Kick và PM nếu Client vẫn đang kết nối
        if is_active and self.is_running:
            self.btn_kick.config(state=tk.NORMAL)
            self.btn_pm.config(state=tk.NORMAL)
        else:
            self.btn_kick.config(state=tk.DISABLED)
            self.btn_pm.config(state=tk.DISABLED)

        self.btn_copy_info.config(state=tk.NORMAL)

    def _refresh_kpis(self):
        """Cập nhật các số liệu thống kê ở hàng thẻ trên cùng."""
        if self.server:
            stats = self.server.get_stats()
            self.lbl_val_online.config(text=str(stats['online']))
            self.lbl_val_total_conns.config(text=str(stats['total_connections']))
            self.lbl_val_total_msgs.config(text=str(stats['total_messages']))
        else:
            self.lbl_val_online.config(text="0")

    def _append_log(self, timestamp, message, tag):
        """Ghi dòng nhật ký mới vào khung văn bản với màu sắc tương ứng."""
        self.txt_log.config(state=tk.NORMAL)

        # In thời gian
        self.txt_log.insert(tk.END, f"[{timestamp}] ", "TIME")

        # In nội dung với tag
        self.txt_log.insert(tk.END, f"{message}\n", tag)

        if self.auto_scroll_var.get():
            self.txt_log.see(tk.END)

        self.txt_log.config(state=tk.DISABLED)

    def action_clear_log(self):
        """Xóa trắng nội dung nhật ký hiện tại."""
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def action_save_log(self):
        """Xuất nội dung nhật ký máy chủ ra file văn bản (.txt)."""
        content = self.txt_log.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Thông báo", "Nhật ký hiện đang trống.")
            return

        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Lưu Nhật Ký Server",
            defaultextension=".txt",
            filetypes=[("Text Files (*.txt)", "*.txt"), ("All Files (*.*)", "*.*")],
            initialfile=f"server_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Thành công", f"Đã lưu nhật ký vào file:\n{filename}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def action_toggle_server(self):
        """Bật hoặc Tắt Server dựa trên trạng thái hiện tại."""
        if self.is_running:
            # Xác nhận trước khi tắt
            confirm = messagebox.askyesno(
                "Xác nhận tắt Server",
                "Bạn có chắc chắn muốn tắt Server?\nTất cả kết nối của Client sẽ bị ngắt!",
                parent=self.root
            )
            if confirm:
                self._stop_server()
        else:
            self._start_server()

    def _start_server(self):
        """Khởi động máy chủ TCP."""
        host = self.entry_host.get().strip()
        port_str = self.entry_port.get().strip()

        if not host:
            messagebox.showerror("Lỗi", "Địa chỉ IP Host không được để trống.", parent=self.root)
            return

        try:
            port = int(port_str)
            if port < 1024 or port > 65535:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Lỗi", "Port phải là một số nguyên từ 1024 đến 65535.", parent=self.root)
            return

        # Khởi tạo ChatServer
        self.server = ChatServer(host=host, port=port)

        # Đăng ký các hook callback
        self.server.add_callback('on_status', lambda active, h, p: self.event_queue.put(('status', (active, h, p))))
        self.server.add_callback('on_log', lambda ts, msg, tag: self.event_queue.put(('log', (ts, msg, tag))))
        self.server.add_callback('on_client_connect', lambda data: self.event_queue.put(('client_connect', data)))
        self.server.add_callback('on_client_join', lambda data: self.event_queue.put(('client_join', data)))
        self.server.add_callback('on_client_update', lambda data: self.event_queue.put(('client_update', data)))
        self.server.add_callback('on_client_leave', lambda data: self.event_queue.put(('client_leave', data)))
        self.server.add_callback('on_message', lambda data: self.event_queue.put(('message', data)))

        ok, msg = self.server.start_threaded()
        if not ok:
            messagebox.showerror("Lỗi Khởi Động", f"Không thể khởi động Server:\n{msg}", parent=self.root)
            self.server = None

    def _stop_server(self):
        """Tắt máy chủ an toàn."""
        if self.server:
            self.server.shutdown()
            self.server = None

    def _handle_status_update(self, is_active, host, port):
        """Cập nhật trạng thái hiển thị của Server trên UI."""
        self.is_running = is_active

        if is_active:
            self.start_time = time.time()
            self.lbl_server_status_badge.config(
                text=f"● ĐANG LẮNG NGHE ({host}:{port})",
                bg=self.COLOR_SUCCESS
            )
            self.btn_toggle_server.config(
                text="⏹ Dừng Server",
                style="Danger.TButton"
            )
            self.entry_host.config(state="disabled")
            self.entry_port.config(state="disabled")
            self.lbl_status_msg.config(text=f"🟢 Server đang chạy trên {host}:{port} - Sẵn sàng nhận Client.")
        else:
            self.start_time = None
            self.lbl_server_status_badge.config(
                text="● ĐÃ DỪNG (STOPPED)",
                bg=self.COLOR_DANGER
            )
            self.btn_toggle_server.config(
                text="▶ Khởi Động Server",
                style="Success.TButton"
            )
            self.entry_host.config(state="normal")
            self.entry_port.config(state="normal")
            self.lbl_status_msg.config(text="🔴 Server đã dừng. Nhấn 'Khởi Động Server' để bắt đầu.")

        self._refresh_kpis()
        self._update_selected_action_bar()

    def action_kick_selected(self):
        """Ngắt kết nối Client đang được chọn."""
        if not self.selected_client_id or not self.server:
            return

        client = self.client_records.get(self.selected_client_id)
        if not client:
            return

        cid = client['id']
        uname = client['username']

        confirm = messagebox.askyesno(
            "Xác nhận Kick",
            f"Bạn có chắc muốn ngắt kết nối Client ID #{cid} ('{uname}')?",
            parent=self.root
        )
        if confirm:
            ok, msg = self.server.kick_client(cid, reason="Quản trị viên đã ngắt kết nối bạn.")
            if ok:
                self.lbl_status_msg.config(text=f"✅ Đã ngắt kết nối Client ID #{cid} ('{uname}').")
            else:
                messagebox.showwarning("Thông báo", msg, parent=self.root)

    def action_pm_selected(self):
        """Mở cửa sổ gửi tin nhắn riêng từ Quản trị viên tới Client được chọn."""
        if not self.selected_client_id or not self.server:
            return

        client = self.client_records.get(self.selected_client_id)
        if not client:
            return

        cid = client['id']
        uname = client['username']

        # Hộp thoại nhập nội dung tin nhắn riêng
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Gửi Tin Nhắn Riêng Tới Client #{cid}")
        dialog.geometry("450x220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        lbl_info = tk.Label(
            dialog,
            text=f"Gửi tin nhắn riêng tới Client ID #{cid} ('{uname}'):",
            font=("Segoe UI", 10, "bold"),
            fg=self.COLOR_PRIMARY,
            padx=14,
            pady=10
        )
        lbl_info.pack(anchor=tk.W)

        entry_msg = ttk.Entry(dialog, width=45, style="Custom.TEntry")
        entry_msg.pack(fill=tk.X, padx=14, pady=5)
        entry_msg.focus_set()

        def do_send():
            text = entry_msg.get().strip()
            if not text:
                return
            ok, res = self.server.send_private_admin(cid, text)
            if ok:
                dialog.destroy()
            else:
                messagebox.showerror("Lỗi", res, parent=dialog)

        entry_msg.bind("<Return>", lambda e: do_send())

        btn_box = tk.Frame(dialog, padx=14, pady=10)
        btn_box.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_box, text="Gửi Tin", style="Primary.TButton", command=do_send).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Hủy", style="Secondary.TButton", command=dialog.destroy).pack(side=tk.RIGHT)

    def action_copy_client_info(self):
        """Sao chép thông tin Client được chọn vào bộ nhớ tạm (Clipboard)."""
        if not self.selected_client_id or self.selected_client_id not in self.client_records:
            return

        c = self.client_records[self.selected_client_id]
        info_text = (
            f"Client ID: #{c['id']}\n"
            f"Username: {c['username']}\n"
            f"IP & Port: {c['address']}\n"
            f"Socket FD: {c['fileno']}\n"
            f"Connected At: {c['connected_at']}\n"
            f"Status: {c['status']}\n"
            f"Messages: {c['msg_count']}"
        )
        self.root.clipboard_clear()
        self.root.clipboard_append(info_text)
        self.lbl_status_msg.config(text=f"📋 Đã sao chép thông tin Client ID #{c['id']} vào Clipboard.")

    def action_broadcast(self):
        """Gửi thông báo hệ thống tới tất cả Client đang online."""
        if not self.is_running or not self.server:
            messagebox.showwarning("Thông báo", "Server hiện chưa hoạt động. Hãy khởi động Server trước.", parent=self.root)
            return

        text = self.entry_broadcast.get().strip()
        if not text:
            return

        ok, msg = self.server.broadcast_announcement(text)
        if ok:
            self.entry_broadcast.delete(0, tk.END)
            self.lbl_status_msg.config(text="📢 Đã phát thông báo thành công tới tất cả Client.")
        else:
            messagebox.showerror("Lỗi", msg, parent=self.root)

    def on_closing(self):
        """Xử lý đóng ứng dụng an toàn khi người dùng nhấn nút X."""
        if self.is_running:
            confirm = messagebox.askyesno(
                "Đóng ứng dụng",
                "Server vẫn đang chạy. Bạn có chắc chắn muốn tắt Server và thoát không?",
                parent=self.root
            )
            if not confirm:
                return

        self._stop_server()
        self.root.destroy()
