#!/usr/bin/env python3
"""
Trung Tâm Quản Trị & Điều Phối Phiên Họp Server (Meet Server Controller GUI).
Seminar Lập Trình Mạng: Hệ Thống Hội Nghị Trực Tuyến & Chat Client - Server.

Cung cấp giao diện đồ họa Desktop (Tkinter) chuyên nghiệp quản lý:
1. Đa phòng họp (Meeting Rooms): Tạo phòng, Khóa phòng, Mute All, Giải tán phòng.
2. Danh sách người tham gia theo từng phòng (Desktop App & TCP Socket Client).
3. Điều khiển thành viên: Kích, Tắt tiếng (Mute/Unmute), Gửi tin nhắn riêng.
4. Phát thông báo khẩn toàn máy chủ hoặc theo từng phòng cụ thể.
5. Live Logs & Thống kê lưu lượng mạng thời gian thực.
"""

import os
import sys
import queue
import threading
import time
import socket
import asyncio
import subprocess
import platform
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Tự động nạp site-packages từ .venv nếu có
venv_lib = os.path.join(BASE_DIR, '.venv', 'lib')
if os.path.isdir(venv_lib):
    for d in os.listdir(venv_lib):
        sp = os.path.join(venv_lib, d, 'site-packages')
        if os.path.isdir(sp) and sp not in sys.path:
            sys.path.insert(0, sp)

import config
from server.hub_server import DualChatHub, start_dual_server, HOST, WEB_PORT, TCP_PORT
from server.rooms import room_manager, MeetingRoom


def get_local_lan_ip():
    """Lấy địa chỉ IP mạng LAN nội bộ của máy."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class ServerGUI:
    # Hệ màu chuẩn Desktop Admin Tool (Light, Clean, Professional & High Contrast)
    COLOR_APP_BG = "#F5F6F8"       # Nền ứng dụng chính
    COLOR_CARD = "#FFFFFF"         # Vùng bảng, thẻ, nội dung
    COLOR_BORDER = "#D0D5DD"       # Viền chuẩn
    COLOR_BORDER_LIGHT = "#E5E7EB" # Viền phân cách mỏng
    COLOR_TEXT = "#1F2937"         # Chữ chính: xám đen đậm, độ tương phản cao
    COLOR_MUTED = "#4B5563"        # Chữ phụ: xám đậm dễ đọc, không bị nhạt
    COLOR_HINT = "#667085"         # Chữ phụ cấp 2: rõ ràng trên nền trắng
    COLOR_PRIMARY = "#2563EB"      # Màu nhấn xanh duy nhất
    COLOR_PRIMARY_HOVER = "#1D4ED8"
    COLOR_SUCCESS = "#16A34A"      # Xanh lá: trực tuyến / thành công
    COLOR_DANGER = "#DC2626"       # Đỏ: dừng / lỗi / nguy hiểm
    COLOR_DANGER_BG = "#FEF2F2"    # Nền đỏ nhạt nút danger
    COLOR_DANGER_BORDER = "#FECACA"
    COLOR_WARNING = "#D97706"      # Cam cảnh báo
    COLOR_WARNING_BG = "#FFFBEB"
    COLOR_WARNING_BORDER = "#FDE68A"
    COLOR_SELECT_BG = "#EFF6FF"    # Nền hàng bảng được chọn (xanh nhạt)
    COLOR_SELECT_FG = "#111827"    # Chữ hàng bảng được chọn (màu tối tương phản cao)

    # Font chữ hệ thống có hỗ trợ tiếng Việt hoàn chỉnh
    FONT_FAMILY = "Segoe UI" if platform.system() == "Windows" else "Liberation Sans"
    FONT_MONO = "Consolas" if platform.system() == "Windows" else "Liberation Mono"

    # Hệ cỡ chữ chuẩn hóa theo pixel (trong Tkinter, số nguyên âm = kích thước hiển thị chính xác theo pixel)
    FONT_TITLE = (FONT_FAMILY, -21, "bold")         # 21 px, semibold
    FONT_SECTION = (FONT_FAMILY, -16, "bold")       # 16 px, semibold
    FONT_BODY = (FONT_FAMILY, -14)                  # 14 px, regular
    FONT_BODY_BOLD = (FONT_FAMILY, -14, "bold")     # 14 px, bold
    FONT_BUTTON = (FONT_FAMILY, -14)                # 14 px, button medium
    FONT_BUTTON_BOLD = (FONT_FAMILY, -14, "bold")   # 14 px, button bold
    FONT_SUB = (FONT_FAMILY, -12)                   # 12 px, thông tin phụ (không nhỏ hơn 12px)
    FONT_SUB_BOLD = (FONT_FAMILY, -12, "bold")      # 12 px, nhãn thống kê
    FONT_KPI_VAL = (FONT_FAMILY, -24, "bold")       # 24 px, giá trị thống kê to rõ
    FONT_LOG = (FONT_MONO, -13)                     # 13 px, monospace cho terminal logs

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Quản trị máy chủ - Seminar Lập Trình Mạng")
        self.root.geometry("1240x800")
        self.root.minsize(1080, 700)
        self.root.configure(bg=self.COLOR_APP_BG)

        # Xử lý đóng cửa sổ an toàn
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Trạng thái Server & Async Event Loop
        self.hub = None
        self.is_running = False
        self.server_thread = None
        self.server_loop = None
        self.stop_event = None
        self.start_time = None
        self.event_queue = queue.Queue()

        # Dữ liệu lựa chọn trên GUI
        self.selected_room_code = "seminar-network-lab"
        self.selected_client_id = None
        self.lan_ip = get_local_lan_ip()

        # Cấu hình biến Tkinter
        self.host_var = tk.StringVar(value=HOST)
        self.hub_port_var = tk.StringVar(value=str(WEB_PORT))
        self.tcp_port_var = tk.StringVar(value=str(TCP_PORT))

        # Thiết lập style & giao diện
        self._setup_styles()
        self._build_ui()

        # Nạp dữ liệu ban đầu
        self.refresh_all_data()

        # Vòng lặp nhận sự kiện từ Async Loop
        self.root.after(50, self._process_events)
        # Vòng lặp cập nhật KPI & Uptime
        self.root.after(1000, self._update_clock_tick)

        # Tự động khởi động Server khi mở GUI
        self.root.after(300, self.start_server)

    def run(self):
        """Chạy giao diện chính."""
        self.root.mainloop()

    # ─────────────────────────────────────────────────────────────────
    # STYLES & THEMING (Typography & Component Sizing)
    # ─────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        style.configure(".", font=self.FONT_BODY, background=self.COLOR_APP_BG)

        # 1. Primary Button (Chiều cao 36-38px, chữ 14px bold)
        style.configure(
            "Primary.TButton",
            font=self.FONT_BUTTON_BOLD,
            background=self.COLOR_PRIMARY,
            foreground="#FFFFFF",
            padding=(14, 8),
            borderwidth=1,
            bordercolor=self.COLOR_PRIMARY_HOVER,
            relief="flat"
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.COLOR_PRIMARY_HOVER), ("disabled", "#93C5FD")],
            foreground=[("disabled", "#EFF6FF")]
        )

        # 2. Secondary Button (Nút trung tính nền trắng, chiều cao 36-38px, chữ 14px)
        style.configure(
            "Secondary.TButton",
            font=self.FONT_BUTTON,
            background=self.COLOR_CARD,
            foreground=self.COLOR_TEXT,
            padding=(12, 8),
            borderwidth=1,
            bordercolor=self.COLOR_BORDER,
            relief="flat"
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#F3F4F6"), ("disabled", "#F9FAFB")],
            foreground=[("disabled", self.COLOR_HINT)]
        )

        # 3. Danger Button (Hành động nguy hiểm / dừng máy chủ: nền đỏ nhẹ, chữ 14px)
        style.configure(
            "Danger.TButton",
            font=self.FONT_BUTTON,
            background=self.COLOR_DANGER_BG,
            foreground=self.COLOR_DANGER,
            padding=(12, 8),
            borderwidth=1,
            bordercolor=self.COLOR_DANGER_BORDER,
            relief="flat"
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#FEE2E2"), ("disabled", self.COLOR_DANGER_BG)],
            foreground=[("disabled", "#FCA5A5")]
        )

        # 4. Success Button (Khởi động Server: xanh lá, chữ 14px bold)
        style.configure(
            "Success.TButton",
            font=self.FONT_BUTTON_BOLD,
            background=self.COLOR_SUCCESS,
            foreground="#FFFFFF",
            padding=(14, 8),
            borderwidth=1,
            bordercolor="#15803D",
            relief="flat"
        )
        style.map(
            "Success.TButton",
            background=[("active", "#15803D"), ("disabled", "#86EFAC")],
            foreground=[("disabled", "#EFF6FF")]
        )

        # 5. Warning Button (Tắt âm / cảnh báo nhẹ)
        style.configure(
            "Warning.TButton",
            font=self.FONT_BUTTON,
            background=self.COLOR_WARNING_BG,
            foreground=self.COLOR_WARNING,
            padding=(12, 8),
            borderwidth=1,
            bordercolor=self.COLOR_WARNING_BORDER,
            relief="flat"
        )
        style.map(
            "Warning.TButton",
            background=[("active", "#FEF3C7"), ("disabled", self.COLOR_WARNING_BG)],
            foreground=[("disabled", "#FCD34D")]
        )

        # 6. Entry Style (Chiều cao 35-37px, chữ 14px)
        style.configure(
            "TEntry",
            font=self.FONT_BODY,
            padding=(8, 7)
        )

        # 7. Combobox Style (Chiều cao 35-37px, chữ 14px)
        style.configure(
            "TCombobox",
            font=self.FONT_BODY,
            padding=(8, 7)
        )

        # 8. Notebook Tab Styles (Tab thoáng 20x10 padding, chữ 14px, không cắt chữ)
        style.configure(
            "TNotebook",
            background=self.COLOR_APP_BG,
            borderwidth=0,
            tabmargins=[0, 0, 0, 0]
        )
        style.configure(
            "TNotebook.Tab",
            font=self.FONT_BODY,
            padding=(20, 10),
            background="#E5E7EB",
            foreground=self.COLOR_MUTED,
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.COLOR_CARD)],
            foreground=[("selected", self.COLOR_PRIMARY)],
            font=[("selected", self.FONT_BODY_BOLD)]
        )

        # 9. Treeview Table Styles (Hàng dữ liệu cao 36px, header cao 38px, chữ 14px)
        style.configure(
            "Treeview",
            background=self.COLOR_CARD,
            foreground=self.COLOR_TEXT,
            rowheight=36,
            fieldbackground=self.COLOR_CARD,
            font=self.FONT_BODY,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#F9FAFB",
            foreground="#374151",
            font=self.FONT_BODY_BOLD,
            padding=(8, 7),
            borderwidth=1,
            relief="flat"
        )
        style.map(
            "Treeview",
            background=[("selected", self.COLOR_SELECT_BG)],
            foreground=[("selected", self.COLOR_SELECT_FG)]
        )

    # ─────────────────────────────────────────────────────────────────
    # XÂY DỰNG GIAO DIỆN CHÍNH
    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # 1. Thanh tiêu đề trên cùng (Clean Light Header)
        self._build_header()

        # 2. Dải điều khiển dịch vụ & Chỉ số KPI (Unified Toolbar & Metrics)
        self._build_metric_cards()

        # 3. Khu vực nội dung các Tabs chính
        self._build_main_tabs()

        # 4. Thanh trạng thái đáy trang (Status Bar)
        self._build_status_bar()

    def _build_header(self):
        """Header trên cùng: Tiêu đề 21px, thông tin phụ 12-13px, trạng thái & uptime 14px."""
        header_outer = tk.Frame(self.root, bg=self.COLOR_CARD)
        header_outer.pack(fill=tk.X, side=tk.TOP)

        header = tk.Frame(header_outer, bg=self.COLOR_CARD, height=64, padx=22, pady=10)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Góc trái: Tiêu đề 21px semibold & Subtitle 12-13px
        left_box = tk.Frame(header, bg=self.COLOR_CARD)
        left_box.pack(side=tk.LEFT, fill=tk.Y)

        lbl_title = tk.Label(
            left_box,
            text="Quản trị máy chủ",
            font=self.FONT_TITLE,
            fg=self.COLOR_TEXT,
            bg=self.COLOR_CARD
        )
        lbl_title.pack(anchor=tk.W)

        lbl_sub = tk.Label(
            left_box,
            text=f"Hệ thống hội nghị trực tuyến • IP LAN: {self.lan_ip}",
            font=self.FONT_SUB,
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        )
        lbl_sub.pack(anchor=tk.W, pady=(2, 0))

        # Góc phải: Chấm trạng thái nhỏ & Thời gian chạy (14px)
        right_box = tk.Frame(header, bg=self.COLOR_CARD)
        right_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_server_status_badge = tk.Label(
            right_box,
            text="● Đã dừng",
            font=self.FONT_BODY_BOLD,
            fg=self.COLOR_DANGER,
            bg=self.COLOR_CARD,
            padx=4,
            pady=2
        )
        self.lbl_server_status_badge.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(
            right_box, text="|", font=self.FONT_BODY,
            fg=self.COLOR_BORDER, bg=self.COLOR_CARD
        ).pack(side=tk.LEFT, padx=(0, 14))

        self.lbl_uptime = tk.Label(
            right_box,
            text="Thời gian chạy: 00:00:00",
            font=self.FONT_BODY,
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        )
        self.lbl_uptime.pack(side=tk.LEFT)

        sep = tk.Frame(header_outer, bg=self.COLOR_BORDER_LIGHT, height=1)
        sep.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_metric_cards(self):
        """Dải điều khiển dịch vụ và 4 thẻ thống kê được trình bày nhất quán trên cùng một hàng."""
        container = tk.Frame(self.root, bg=self.COLOR_APP_BG, padx=16, pady=10)
        container.pack(fill=tk.X, side=tk.TOP)

        container.columnconfigure(0, weight=5)  # Thẻ điều khiển dịch vụ
        container.columnconfigure(1, weight=2)  # Số phiên họp
        container.columnconfigure(2, weight=2)  # Thành viên online
        container.columnconfigure(3, weight=2)  # Tổng tin nhắn
        container.columnconfigure(4, weight=2)  # Lưu lượng mạng

        # --- Khối 1: Điều Khiển Dịch Vụ Máy Chủ ---
        card_ctrl = tk.Frame(
            container, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=10
        )
        card_ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        lbl_ctrl_title = tk.Label(
            card_ctrl, text="ĐIỀU KHIỂN DỊCH VỤ",
            font=self.FONT_SUB_BOLD, fg=self.COLOR_MUTED, bg=self.COLOR_CARD
        )
        lbl_ctrl_title.pack(anchor=tk.W)

        ctrl_row = tk.Frame(card_ctrl, bg=self.COLOR_CARD, pady=4)
        ctrl_row.pack(fill=tk.X)

        tk.Label(ctrl_row, text="Hub Port:", font=self.FONT_BODY, bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(side=tk.LEFT)
        ent_hub_port = ttk.Entry(ctrl_row, textvariable=self.hub_port_var, width=7, style="TEntry")
        ent_hub_port.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(ctrl_row, text="TCP Port:", font=self.FONT_BODY, bg=self.COLOR_CARD, fg=self.COLOR_MUTED).pack(side=tk.LEFT)
        ent_tcp_port = ttk.Entry(ctrl_row, textvariable=self.tcp_port_var, width=7, style="TEntry")
        ent_tcp_port.pack(side=tk.LEFT, padx=(4, 14))

        self.btn_toggle_server = ttk.Button(
            ctrl_row, text="Bật máy chủ", style="Success.TButton", command=self.toggle_server
        )
        self.btn_toggle_server.pack(side=tk.LEFT, padx=(0, 8))

        btn_open_app = ttk.Button(
            ctrl_row, text="Mở Desktop App", style="Secondary.TButton", command=self.open_desktop_app
        )
        btn_open_app.pack(side=tk.LEFT)

        # --- Khối 2: KPI Phiên Họp ---
        self.lbl_kpi_rooms = self._create_kpi_card(container, 1, "PHIÊN HỌP", "1", "Phòng đang mở")

        # --- Khối 3: KPI Thành Viên Online ---
        self.lbl_kpi_online = self._create_kpi_card(container, 2, "TRỰC TUYẾN", "0", "Desktop & TCP")

        # --- Khối 4: KPI Tổng Tin Nhắn ---
        self.lbl_kpi_messages = self._create_kpi_card(container, 3, "TỔNG TIN NHẮN", "0", "Chat & Whisper")

        # --- Khối 5: KPI Lưu Lượng Mạng ---
        self.lbl_kpi_traffic = self._create_kpi_card(container, 4, "LƯU LƯỢNG", "0 B", "Dữ liệu truyền tải")

    def _create_kpi_card(self, parent, col, title, initial_val, subtext):
        """Tạo thẻ thống kê với typography rõ nét (giá trị 24px, nhãn phụ 12px không mờ)."""
        card = tk.Frame(
            parent, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=10
        )
        card.grid(row=0, column=col, sticky="nsew", padx=3)

        tk.Label(
            card, text=title, font=self.FONT_SUB_BOLD,
            fg=self.COLOR_MUTED, bg=self.COLOR_CARD
        ).pack(anchor=tk.W)

        lbl_val = tk.Label(
            card, text=initial_val, font=self.FONT_KPI_VAL,
            fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        )
        lbl_val.pack(anchor=tk.W, pady=(2, 1))

        tk.Label(
            card, text=subtext, font=self.FONT_SUB,
            fg=self.COLOR_HINT, bg=self.COLOR_CARD
        ).pack(anchor=tk.W)

        return lbl_val

    def _build_main_tabs(self):
        container = tk.Frame(self.root, bg=self.COLOR_APP_BG, padx=16, pady=2)
        container.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Quản lý Phiên Họp
        self.tab_rooms = tk.Frame(self.notebook, bg=self.COLOR_APP_BG, padx=4, pady=6)
        self.notebook.add(self.tab_rooms, text=" Quản lý phiên họp ")
        self._build_rooms_tab()

        # Tab 2: Toàn Bộ Client
        self.tab_clients = tk.Frame(self.notebook, bg=self.COLOR_APP_BG, padx=4, pady=6)
        self.notebook.add(self.tab_clients, text=" Toàn bộ Client ")
        self._build_clients_tab()

        # Tab 3: Phát Thông Báo
        self.tab_broadcast = tk.Frame(self.notebook, bg=self.COLOR_APP_BG, padx=4, pady=6)
        self.notebook.add(self.tab_broadcast, text=" Phát thông báo ")
        self._build_broadcast_tab()

        # Tab 4: Nhật Ký Máy Chủ
        self.tab_logs = tk.Frame(self.notebook, bg=self.COLOR_APP_BG, padx=4, pady=6)
        self.notebook.add(self.tab_logs, text=" Nhật ký máy chủ ")
        self._build_logs_tab()

    # ─────────────────────────────────────────────────────────────────
    # TAB 1: QUẢN LÝ PHIÊN HỌP (MEETING ROOMS & PARTICIPANTS)
    # ─────────────────────────────────────────────────────────────────
    def _build_rooms_tab(self):
        # Chia đôi khung: Nửa trên danh sách phòng, Nửa dưới thành viên trong phòng đang chọn
        paned = tk.PanedWindow(self.tab_rooms, orient=tk.VERTICAL, bg=self.COLOR_APP_BG, sashwidth=6, bd=0)
        paned.pack(fill=tk.BOTH, expand=True)

        # === 1. KHUNG TRÊN: PHÒNG HỌP ===
        frame_rooms_box = tk.Frame(
            paned, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1
        )
        paned.add(frame_rooms_box, height=290)

        # Toolbar trên bảng phòng họp
        toolbar_rooms = tk.Frame(frame_rooms_box, bg=self.COLOR_CARD, padx=14, pady=10)
        toolbar_rooms.pack(fill=tk.X)

        lbl_rooms_header = tk.Label(
            toolbar_rooms, text="Phòng họp",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        )
        lbl_rooms_header.pack(side=tk.LEFT)

        btn_refresh_rooms = ttk.Button(toolbar_rooms, text="Làm mới", style="Secondary.TButton", command=self.refresh_rooms_list)
        btn_refresh_rooms.pack(side=tk.RIGHT, padx=4)

        btn_disband_room = ttk.Button(toolbar_rooms, text="Giải tán phòng", style="Danger.TButton", command=self.on_disband_room)
        btn_disband_room.pack(side=tk.RIGHT, padx=4)

        btn_mute_room = ttk.Button(toolbar_rooms, text="Tắt âm phòng", style="Secondary.TButton", command=self.on_mute_room)
        btn_mute_room.pack(side=tk.RIGHT, padx=4)

        self.btn_lock_room = ttk.Button(toolbar_rooms, text="Khóa / Mở khóa", style="Secondary.TButton", command=self.on_toggle_lock_room)
        self.btn_lock_room.pack(side=tk.RIGHT, padx=4)

        btn_new_room = ttk.Button(toolbar_rooms, text="Tạo cuộc họp", style="Primary.TButton", command=self.open_create_room_modal)
        btn_new_room.pack(side=tk.RIGHT, padx=4)

        # Bảng Treeview danh sách phòng
        tree_container = tk.Frame(frame_rooms_box, bg=self.COLOR_CARD)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns_room = ("code", "title", "host", "online", "locked", "chat", "created_at")
        self.tree_rooms = ttk.Treeview(tree_container, columns=columns_room, show="headings", selectmode="browse")

        self.tree_rooms.heading("code", text="Mã phòng")
        self.tree_rooms.heading("title", text="Tên cuộc họp")
        self.tree_rooms.heading("host", text="Chủ trì")
        self.tree_rooms.heading("online", text="Trực tuyến")
        self.tree_rooms.heading("locked", text="Bảo mật")
        self.tree_rooms.heading("chat", text="Chat chung")
        self.tree_rooms.heading("created_at", text="Thời điểm tạo")

        self.tree_rooms.column("code", width=160, anchor=tk.CENTER)
        self.tree_rooms.column("title", width=280, anchor=tk.W)
        self.tree_rooms.column("host", width=160, anchor=tk.W)
        self.tree_rooms.column("online", width=90, anchor=tk.CENTER)
        self.tree_rooms.column("locked", width=100, anchor=tk.CENTER)
        self.tree_rooms.column("chat", width=100, anchor=tk.CENTER)
        self.tree_rooms.column("created_at", width=120, anchor=tk.CENTER)

        sb_rooms = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree_rooms.yview)
        self.tree_rooms.configure(yscrollcommand=sb_rooms.set)

        self.tree_rooms.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_rooms.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_rooms.bind("<<TreeviewSelect>>", self.on_room_select)

        # === 2. KHUNG DƯỚI: THÀNH VIÊN TRONG PHÒNG ĐANG CHỌN ===
        frame_members_box = tk.Frame(
            paned, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1
        )
        paned.add(frame_members_box, height=270)

        toolbar_members = tk.Frame(frame_members_box, bg=self.COLOR_CARD, padx=14, pady=10)
        toolbar_members.pack(fill=tk.X)

        self.lbl_selected_room_title = tk.Label(
            toolbar_members,
            text="Thành viên trong phòng: seminar-network-lab",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        )
        self.lbl_selected_room_title.pack(side=tk.LEFT)

        btn_whisper_member = ttk.Button(toolbar_members, text="Gửi tin riêng", style="Secondary.TButton", command=self.on_whisper_client)
        btn_whisper_member.pack(side=tk.RIGHT, padx=4)

        btn_mute_member = ttk.Button(toolbar_members, text="Bật/Tắt chat", style="Secondary.TButton", command=self.on_toggle_mute_client)
        btn_mute_member.pack(side=tk.RIGHT, padx=4)

        btn_kick_member = ttk.Button(toolbar_members, text="Kích khỏi phòng", style="Danger.TButton", command=self.on_kick_client)
        btn_kick_member.pack(side=tk.RIGHT, padx=4)

        # Bảng Treeview thành viên trong phòng
        tree_members_container = tk.Frame(frame_members_box, bg=self.COLOR_CARD)
        tree_members_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns_member = ("id", "fullname", "username", "type", "address", "joined_at", "msg_count", "mute_status")
        self.tree_members = ttk.Treeview(tree_members_container, columns=columns_member, show="headings", selectmode="browse")

        self.tree_members.heading("id", text="ID")
        self.tree_members.heading("fullname", text="Tên hiển thị")
        self.tree_members.heading("username", text="Tài khoản")
        self.tree_members.heading("type", text="Nền tảng")
        self.tree_members.heading("address", text="Địa chỉ IP:Port")
        self.tree_members.heading("joined_at", text="Thời điểm vào")
        self.tree_members.heading("msg_count", text="Tin nhắn")
        self.tree_members.heading("mute_status", text="Quyền chat")

        self.tree_members.column("id", width=60, anchor=tk.CENTER)
        self.tree_members.column("fullname", width=180, anchor=tk.W)
        self.tree_members.column("username", width=130, anchor=tk.W)
        self.tree_members.column("type", width=130, anchor=tk.CENTER)
        self.tree_members.column("address", width=170, anchor=tk.CENTER)
        self.tree_members.column("joined_at", width=120, anchor=tk.CENTER)
        self.tree_members.column("msg_count", width=85, anchor=tk.CENTER)
        self.tree_members.column("mute_status", width=120, anchor=tk.CENTER)

        sb_members = ttk.Scrollbar(tree_members_container, orient=tk.VERTICAL, command=self.tree_members.yview)
        self.tree_members.configure(yscrollcommand=sb_members.set)

        self.tree_members.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_members.pack(side=tk.RIGHT, fill=tk.Y)

        # Nhãn thông báo trống rõ ràng, tương phản tốt khi không có thành viên
        self.lbl_members_empty = tk.Label(
            self.tree_members,
            text="Chưa có thành viên nào tham gia phòng này",
            font=self.FONT_BODY,
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        )

    # ─────────────────────────────────────────────────────────────────
    # TAB 2: TOÀN BỘ KẾT NỐI CLIENT (ALL CONNECTED CLIENTS)
    # ─────────────────────────────────────────────────────────────────
    def _build_clients_tab(self):
        card = tk.Frame(
            self.tab_clients, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1
        )
        card.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(card, bg=self.COLOR_CARD, padx=14, pady=10)
        toolbar.pack(fill=tk.X)

        tk.Label(
            toolbar, text="Danh sách Client kết nối máy chủ",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Làm mới", style="Secondary.TButton", command=self.refresh_all_clients).pack(side=tk.RIGHT, padx=4)
        ttk.Button(toolbar, text="Kích kết nối", style="Danger.TButton", command=self.on_kick_from_all_tab).pack(side=tk.RIGHT, padx=4)
        ttk.Button(toolbar, text="Bật/Tắt chat", style="Secondary.TButton", command=self.on_mute_from_all_tab).pack(side=tk.RIGHT, padx=4)

        tree_box = tk.Frame(card, bg=self.COLOR_CARD)
        tree_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        columns = ("id", "username", "fullname", "room", "type", "address", "joined_at", "msg_count", "status")
        self.tree_all_clients = ttk.Treeview(tree_box, columns=columns, show="headings", selectmode="browse")

        self.tree_all_clients.heading("id", text="ID")
        self.tree_all_clients.heading("username", text="Tài khoản")
        self.tree_all_clients.heading("fullname", text="Họ và tên")
        self.tree_all_clients.heading("room", text="Phòng tham gia")
        self.tree_all_clients.heading("type", text="Loại kết nối")
        self.tree_all_clients.heading("address", text="Địa chỉ IP:Port")
        self.tree_all_clients.heading("joined_at", text="Kết nối lúc")
        self.tree_all_clients.heading("msg_count", text="Tin nhắn")
        self.tree_all_clients.heading("status", text="Trạng thái")

        self.tree_all_clients.column("id", width=60, anchor=tk.CENTER)
        self.tree_all_clients.column("username", width=130, anchor=tk.W)
        self.tree_all_clients.column("fullname", width=180, anchor=tk.W)
        self.tree_all_clients.column("room", width=160, anchor=tk.CENTER)
        self.tree_all_clients.column("type", width=130, anchor=tk.CENTER)
        self.tree_all_clients.column("address", width=170, anchor=tk.CENTER)
        self.tree_all_clients.column("joined_at", width=120, anchor=tk.CENTER)
        self.tree_all_clients.column("msg_count", width=85, anchor=tk.CENTER)
        self.tree_all_clients.column("status", width=110, anchor=tk.CENTER)

        sb = ttk.Scrollbar(tree_box, orient=tk.VERTICAL, command=self.tree_all_clients.yview)
        self.tree_all_clients.configure(yscrollcommand=sb.set)

        self.tree_all_clients.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_clients_empty = tk.Label(
            self.tree_all_clients,
            text="Chưa có client nào kết nối tới máy chủ",
            font=self.FONT_BODY,
            fg=self.COLOR_MUTED,
            bg=self.COLOR_CARD
        )

    # ─────────────────────────────────────────────────────────────────
    # TAB 3: PHÁT THÔNG BÁO HỆ THỐNG (BROADCAST ANNOUNCEMENT)
    # ─────────────────────────────────────────────────────────────────
    def _build_broadcast_tab(self):
        card = tk.Frame(
            self.tab_broadcast, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=24, pady=20
        )
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            card, text="Phát thông báo hệ thống",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).pack(anchor=tk.W, pady=(0, 4))

        tk.Label(
            card, text="Thông báo sẽ được gửi tức thì đến các client trong phạm vi đã chọn.",
            font=self.FONT_SUB, fg=self.COLOR_MUTED, bg=self.COLOR_CARD
        ).pack(anchor=tk.W, pady=(0, 16))

        target_row = tk.Frame(card, bg=self.COLOR_CARD)
        target_row.pack(fill=tk.X, pady=(0, 14))

        tk.Label(target_row, text="Phạm vi phát thông báo:", font=self.FONT_BODY_BOLD, bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(side=tk.LEFT, padx=(0, 12))
        self.combo_broadcast_target = ttk.Combobox(target_row, width=48, state="readonly", style="TCombobox")
        self.combo_broadcast_target.pack(side=tk.LEFT)
        self.combo_broadcast_target["values"] = ["Toàn bộ hệ thống (Tất cả các phòng)"]
        self.combo_broadcast_target.current(0)

        tk.Label(card, text="Nội dung thông báo:", font=self.FONT_BODY_BOLD, bg=self.COLOR_CARD, fg=self.COLOR_TEXT).pack(anchor=tk.W, pady=(4, 6))
        self.txt_broadcast_msg = scrolledtext.ScrolledText(
            card, height=7, font=self.FONT_BODY, relief=tk.SOLID, bd=1,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1
        )
        self.txt_broadcast_msg.pack(fill=tk.X, pady=(0, 14))

        btn_row = tk.Frame(card, bg=self.COLOR_CARD)
        btn_row.pack(fill=tk.X)

        btn_send = ttk.Button(btn_row, text="Phát thông báo", style="Primary.TButton", command=self.on_send_broadcast)
        btn_send.pack(side=tk.LEFT, padx=(0, 8))

        btn_clear = ttk.Button(btn_row, text="Xóa nội dung", style="Secondary.TButton", command=lambda: self.txt_broadcast_msg.delete("1.0", tk.END))
        btn_clear.pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────
    # TAB 4: NHẬT KÝ MÁY CHỦ & GÓI TIN MẠNG (LIVE LOGS)
    # ─────────────────────────────────────────────────────────────────
    def _build_logs_tab(self):
        card = tk.Frame(
            self.tab_logs, bg=self.COLOR_CARD, bd=1, relief=tk.SOLID,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1, padx=14, pady=10
        )
        card.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(card, bg=self.COLOR_CARD)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            toolbar, text="Nhật ký máy chủ thời gian thực",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_CARD
        ).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Xóa nhật ký", style="Secondary.TButton", command=self.clear_logs).pack(side=tk.RIGHT, padx=4)
        ttk.Button(toolbar, text="Lưu ra file", style="Secondary.TButton", command=self.export_logs).pack(side=tk.RIGHT, padx=4)

        # ScrolledText hiển thị logs tô màu cú pháp
        self.txt_logs = scrolledtext.ScrolledText(
            card, bg="#0F172A", fg="#F8FAFC", font=self.FONT_LOG,
            insertbackground="#FFFFFF", relief=tk.FLAT, bd=0
        )
        self.txt_logs.pack(fill=tk.BOTH, expand=True)

        # Định dạng màu cho các Tag log
        self.txt_logs.tag_config("SUCCESS", foreground="#22C55E")  # Xanh lục
        self.txt_logs.tag_config("INFO", foreground="#38BDF8")     # Xanh dương nhạt
        self.txt_logs.tag_config("JOIN", foreground="#14B8A6")     # Teal
        self.txt_logs.tag_config("LEAVE", foreground="#94A3B8")    # Slate xám
        self.txt_logs.tag_config("CHAT", foreground="#A78BFA")     # Tím pastel
        self.txt_logs.tag_config("FILE", foreground="#F472B6")     # Hồng
        self.txt_logs.tag_config("ROOM", foreground="#FBBF24")     # Vàng hổ phách
        self.txt_logs.tag_config("WARNING", foreground="#F97316")  # Cam
        self.txt_logs.tag_config("ERROR", foreground="#EF4444")    # Đỏ
        self.txt_logs.tag_config("SYSTEM", foreground="#CBD5E1")   # Xám sáng

    def _build_status_bar(self):
        """Thanh trạng thái dưới cùng: Tối giản, thanh mảnh, chữ 12-13px rõ nét."""
        sep = tk.Frame(self.root, bg=self.COLOR_BORDER_LIGHT, height=1)
        sep.pack(fill=tk.X, side=tk.BOTTOM)

        status_bar = tk.Frame(self.root, bg="#F9FAFB", height=30, padx=18)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.lbl_status_left = tk.Label(
            status_bar,
            text=f"Asyncio Dual Hub Engine • Cổng dịch vụ: {WEB_PORT} (Hub/Desktop) & {TCP_PORT} (TCP Socket)",
            font=self.FONT_SUB, bg="#F9FAFB", fg=self.COLOR_MUTED
        )
        self.lbl_status_left.pack(side=tk.LEFT)

        self.lbl_status_right = tk.Label(
            status_bar,
            text=f"Mạng LAN: {self.lan_ip} • Trạng thái: Sẵn sàng",
            font=self.FONT_SUB, bg="#F9FAFB", fg=self.COLOR_MUTED
        )
        self.lbl_status_right.pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────────
    # QUẢN LÝ TIẾN TRÌNH SERVER & ASYNCIO THREAD
    # ─────────────────────────────────────────────────────────────────
    def _free_port(self, port: int):
        """Giải phóng cổng mạng nếu đang bị tiến trình khác chiếm dụng."""
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
                pids = set()
                for line in out.strip().splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5 and f":{port}" in parts[1]:
                        pids.add(parts[-1])
                for pid in pids:
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(f'lsof -ti :{port} | xargs -r kill -9 2>/dev/null', shell=True)
            time.sleep(0.3)
            return True
        except Exception:
            return False

    def toggle_server(self):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if self.is_running:
            return

        self.is_running = True
        self.btn_toggle_server.configure(text="Đang bật...", state=tk.DISABLED)

        # Chạy máy chủ trong một luồng riêng biệt
        self.server_thread = threading.Thread(target=self._server_worker, daemon=True)
        self.server_thread.start()

    def _server_worker(self):
        """Worker thread chạy asyncio event loop cho Dual Hub Server."""
        self.server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.server_loop)
        self.stop_event = asyncio.Event()

        self.hub = DualChatHub()

        # Đăng ký callback thread-safe vào event_queue
        def _on_log(log_entry):
            self.event_queue.put(('LOG', log_entry))

        def _on_state_change(*args):
            self.event_queue.put(('STATE_CHANGE', None))

        self.hub.on_log = _on_log
        self.hub.on_state_change = _on_state_change

        def _on_ready(hub, success, error):
            self.event_queue.put(('SERVER_READY', (success, error)))

        try:
            h_port = int(self.hub_port_var.get().strip() or WEB_PORT)
            t_port = int(self.tcp_port_var.get().strip() or TCP_PORT)
            host_val = self.host_var.get().strip() or HOST

            self.server_loop.run_until_complete(
                start_dual_server(
                    host=host_val,
                    web_port=h_port,
                    tcp_port=t_port,
                    hub=self.hub,
                    stop_event=self.stop_event,
                    on_ready=_on_ready
                )
            )
        except Exception as e:
            self.event_queue.put(('SERVER_ERROR', str(e)))
        finally:
            try:
                self.server_loop.close()
            except Exception:
                pass
            self.event_queue.put(('SERVER_STOPPED', None))

    def stop_server(self):
        if not self.is_running:
            return
        self.btn_toggle_server.configure(text="Đang dừng...", state=tk.DISABLED)
        if self.server_loop and self.stop_event:
            self.server_loop.call_soon_threadsafe(self.stop_event.set)

    def run_coro(self, coro):
        """Chạy một coroutine trên server event loop một cách thread-safe."""
        if self.server_loop and self.server_loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self.server_loop)
        try:
            coro.close()
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────
    # XỬ LÝ SỰ KIỆN TỪ BACKGROUND THREAD (THREAD-SAFE)
    # ─────────────────────────────────────────────────────────────────
    def _process_events(self):
        try:
            while not self.event_queue.empty():
                evt_type, data = self.event_queue.get_nowait()

                if evt_type == 'SERVER_READY':
                    success, error = data
                    if success:
                        self.is_running = True
                        self.start_time = datetime.now()
                        self.lbl_server_status_badge.configure(
                            text="● Đang hoạt động",
                            fg=self.COLOR_SUCCESS,
                            bg=self.COLOR_CARD
                        )
                        self.btn_toggle_server.configure(
                            text="Dừng máy chủ",
                            style="Danger.TButton",
                            state=tk.NORMAL
                        )
                        self.lbl_status_right.configure(
                            text=f"Mạng LAN: {self.lan_ip} • Trạng thái: Trực tuyến"
                        )
                        self.refresh_all_data()
                    else:
                        self.is_running = False
                        self.lbl_server_status_badge.configure(
                            text="● Lỗi khởi động",
                            fg=self.COLOR_DANGER,
                            bg=self.COLOR_CARD
                        )
                        self.btn_toggle_server.configure(
                            text="Bật máy chủ",
                            style="Success.TButton",
                            state=tk.NORMAL
                        )
                        if "chiếm dụng" in str(error):
                            ask = messagebox.askyesno(
                                "Cổng Đang Bị Chiếm Dụng",
                                f"Không thể bật máy chủ:\n{error}\n\n"
                                "Bạn có muốn tự động giải phóng cổng này và bật lại Server ngay không?"
                            )
                            if ask:
                                h_port = int(self.hub_port_var.get().strip() or WEB_PORT)
                                t_port = int(self.tcp_port_var.get().strip() or TCP_PORT)
                                self._free_port(h_port)
                                self._free_port(t_port)
                                self.root.after(300, self.start_server)
                        else:
                            messagebox.showerror("Lỗi Khởi Động Máy Chủ", f"Không thể bật máy chủ:\n{error}")

                elif evt_type == 'SERVER_STOPPED':
                    self.is_running = False
                    self.start_time = None
                    self.lbl_server_status_badge.configure(
                        text="● Đã dừng",
                        fg=self.COLOR_DANGER,
                        bg=self.COLOR_CARD
                    )
                    self.btn_toggle_server.configure(
                        text="Bật máy chủ",
                        style="Success.TButton",
                        state=tk.NORMAL
                    )
                    self.lbl_uptime.configure(text="Thời gian chạy: 00:00:00")
                    self.lbl_status_right.configure(
                        text=f"Mạng LAN: {self.lan_ip} • Trạng thái: Đã dừng"
                    )
                    self.refresh_all_data()

                elif evt_type == 'LOG':
                    self._append_log_entry(data)

                elif evt_type == 'STATE_CHANGE':
                    self.refresh_all_data()

        except Exception:
            pass

        self.root.after(50, self._process_events)

    def _append_log_entry(self, entry):
        ts = entry.get('timestamp', '')
        tag = entry.get('tag', 'INFO')
        msg = entry.get('message', '')

        line = f"[{ts}] [{tag:7s}] {msg}\n"
        self.txt_logs.insert(tk.END, line, tag)
        self.txt_logs.see(tk.END)

    def _update_clock_tick(self):
        if self.is_running and self.start_time:
            delta = datetime.now() - self.start_time
            seconds = int(delta.total_seconds())
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            self.lbl_uptime.configure(text=f"Thời gian chạy: {h:02d}:{m:02d}:{s:02d}")

            # Cập nhật KPI thống kê định kỳ
            if self.hub:
                stats = self.hub.get_stats()
                self.lbl_kpi_online.configure(text=str(stats.get('online_total', 0)))
                self.lbl_kpi_messages.configure(text=str(stats.get('total_messages', 0)))

                b = stats.get('bytes_transferred', 0)
                if b < 1024:
                    traffic_str = f"{b} B"
                elif b < 1024 * 1024:
                    traffic_str = f"{b / 1024:.1f} KB"
                else:
                    traffic_str = f"{b / (1024 * 1024):.2f} MB"
                self.lbl_kpi_traffic.configure(text=traffic_str)

        self.root.after(1000, self._update_clock_tick)

    # ─────────────────────────────────────────────────────────────────
    # ĐỒNG BỘ DỮ LIỆU & REFRESH GIAO DIỆN
    # ─────────────────────────────────────────────────────────────────
    def refresh_all_data(self):
        self.refresh_rooms_list()
        self.refresh_selected_room_members()
        self.refresh_all_clients()
        self.update_broadcast_combobox()

    def refresh_rooms_list(self):
        """Làm mới danh sách phòng họp trên Treeview."""
        selected_code = None
        sel = self.tree_rooms.selection()
        if sel:
            selected_code = self.tree_rooms.item(sel[0])['values'][0]

        # Xóa các dòng cũ
        for item in self.tree_rooms.get_children():
            self.tree_rooms.delete(item)

        rooms = room_manager.rooms.values()
        self.lbl_kpi_rooms.configure(text=str(len(rooms)))

        target_item = None
        for r in rooms:
            status_lock = "Khóa" if r.is_locked else "Mở"
            status_chat = "Bật" if r.allow_public_chat else "Khóa"
            created_str = r.created_at.strftime("%H:%M:%S")

            item_id = self.tree_rooms.insert(
                "", tk.END,
                values=(r.code, r.title, r.host_fullname or r.host_username, r.online_count, status_lock, status_chat, created_str)
            )

            if selected_code and r.code == selected_code:
                target_item = item_id
            elif not selected_code and r.code == self.selected_room_code:
                target_item = item_id

        if target_item:
            self.tree_rooms.selection_set(target_item)
            self.tree_rooms.focus(target_item)
        elif self.tree_rooms.get_children():
            first_item = self.tree_rooms.get_children()[0]
            self.tree_rooms.selection_set(first_item)
            self.tree_rooms.focus(first_item)

    def on_room_select(self, event):
        sel = self.tree_rooms.selection()
        if not sel:
            return
        values = self.tree_rooms.item(sel[0])['values']
        if values:
            self.selected_room_code = str(values[0])
            self.lbl_selected_room_title.configure(text=f"Thành viên trong phòng: {self.selected_room_code}")
            self.refresh_selected_room_members()

    def refresh_selected_room_members(self):
        """Cập nhật bảng thành viên thuộc phòng đang chọn."""
        for item in self.tree_members.get_children():
            self.tree_members.delete(item)

        room = room_manager.get_room(self.selected_room_code)
        if not room:
            self.lbl_members_empty.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            return

        member_count = 0
        for c in room.clients:
            if not getattr(c, 'is_active', True):
                continue
            member_count += 1
            cid = c.id
            fullname = getattr(c, 'fullname', c.username) or "(Chờ JOIN)"
            username = getattr(c, 'username', "(Chờ JOIN)")
            ctype = "Desktop App" if c.client_type == 'websocket' else "TCP Socket"
            addr = getattr(c, 'address', f"{c.ip}:{c.port}")
            joined = c.connected_at.strftime("%H:%M:%S")
            msgs = getattr(c, 'msg_count', 0)
            mute = "Tắt chat" if getattr(c, 'is_muted', False) else "Được chat"

            self.tree_members.insert(
                "", tk.END,
                values=(cid, fullname, username, ctype, addr, joined, msgs, mute)
            )

        if member_count == 0:
            self.lbl_members_empty.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self.lbl_members_empty.place_forget()

    def refresh_all_clients(self):
        """Làm mới danh sách toàn bộ Client đang kết nối."""
        for item in self.tree_all_clients.get_children():
            self.tree_all_clients.delete(item)

        if not self.hub:
            self.lbl_clients_empty.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            return

        client_count = 0
        for cid, c in self.hub.clients.items():
            if not c.is_active:
                continue
            client_count += 1
            username = c.username or "(Chờ JOIN)"
            fullname = c.fullname or username
            room = getattr(c, 'room_code', 'seminar-network-lab')
            ctype = "Desktop App" if c.client_type == 'websocket' else "TCP Socket"
            addr = getattr(c, 'address', f"{c.ip}:{c.port}")
            joined = c.connected_at.strftime("%H:%M:%S")
            msgs = c.msg_count
            status = "Trực tuyến"

            self.tree_all_clients.insert(
                "", tk.END,
                values=(cid, username, fullname, room, ctype, addr, joined, msgs, status)
            )

        if client_count == 0:
            self.lbl_clients_empty.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self.lbl_clients_empty.place_forget()

    def update_broadcast_combobox(self):
        """Cập nhật danh sách các phòng vào mục tiêu broadcast."""
        rooms = list(room_manager.rooms.keys())
        values = ["Toàn bộ hệ thống (Tất cả các phòng)"]
        for r_code in rooms:
            r = room_manager.get_room(r_code)
            title = r.title if r else r_code
            values.append(f"Phòng: {r_code} - {title}")

        current = self.combo_broadcast_target.get()
        self.combo_broadcast_target["values"] = values
        if current in values:
            self.combo_broadcast_target.set(current)
        else:
            self.combo_broadcast_target.current(0)

    # ─────────────────────────────────────────────────────────────────
    # THAO TÁC PHÒNG HỌP (ROOM CONTROLS)
    # ─────────────────────────────────────────────────────────────────
    def open_create_room_modal(self):
        """Mở hộp thoại tạo cuộc họp mới."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Tạo cuộc họp mới")
        dlg.geometry("500x340")
        dlg.resizable(False, False)
        dlg.configure(bg=self.COLOR_APP_BG)
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(
            dlg, text="Tạo phòng họp trực tuyến",
            font=self.FONT_SECTION, fg=self.COLOR_TEXT, bg=self.COLOR_APP_BG
        ).pack(anchor=tk.W, padx=22, pady=(18, 8))

        frame_fields = tk.Frame(dlg, bg=self.COLOR_APP_BG, padx=22)
        frame_fields.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame_fields, text="Tên cuộc họp:", font=self.FONT_BODY, bg=self.COLOR_APP_BG, fg=self.COLOR_TEXT).pack(anchor=tk.W, pady=(4, 2))
        ent_title = ttk.Entry(frame_fields, width=42, style="TEntry")
        ent_title.pack(fill=tk.X, pady=(0, 8))
        ent_title.insert(0, "Hội Thảo Chuyên Đề Seminar")

        tk.Label(frame_fields, text="Chủ trì (Host):", font=self.FONT_BODY, bg=self.COLOR_APP_BG, fg=self.COLOR_TEXT).pack(anchor=tk.W, pady=(4, 2))
        ent_host = ttk.Entry(frame_fields, width=42, style="TEntry")
        ent_host.pack(fill=tk.X, pady=(0, 8))
        ent_host.insert(0, "Ban Quản Trị")

        tk.Label(frame_fields, text="Mã phòng (để trống để tự sinh ngẫu nhiên):", font=self.FONT_BODY, bg=self.COLOR_APP_BG, fg=self.COLOR_TEXT).pack(anchor=tk.W, pady=(4, 2))
        ent_code = ttk.Entry(frame_fields, width=42, style="TEntry")
        ent_code.pack(fill=tk.X, pady=(0, 14))

        def do_create():
            title = ent_title.get().strip() or "Cuộc Họp Mới"
            host = ent_host.get().strip() or "Ban Quản Trị"
            code = ent_code.get().strip().lower() or None

            if self.hub:
                self.run_coro(self.hub.create_room_admin(title=title, host_username="admin", host_fullname=host, custom_code=code))
            else:
                room_manager.create_room(title=title, host_username="admin", host_fullname=host, custom_code=code)
                self.refresh_all_data()

            dlg.destroy()
            messagebox.showinfo("Thành Công", "Đã khởi tạo phòng họp mới thành công!")

        btn_box = tk.Frame(dlg, bg=self.COLOR_APP_BG, padx=22, pady=14)
        btn_box.pack(fill=tk.X)

        ttk.Button(btn_box, text="Xác nhận tạo", style="Primary.TButton", command=do_create).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Hủy", style="Secondary.TButton", command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

    def on_toggle_lock_room(self):
        """Khóa hoặc mở khóa phòng đang chọn."""
        if not self.selected_room_code:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một phòng họp trong danh sách!")
            return

        if self.hub:
            self.run_coro(self.hub.admin_toggle_lock_room(self.selected_room_code))
        else:
            room = room_manager.get_room(self.selected_room_code)
            if room:
                room.is_locked = not room.is_locked
                self.refresh_rooms_list()

    def on_mute_room(self):
        """Mute all các thành viên trong phòng đang chọn."""
        if not self.selected_room_code:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một phòng họp trong danh sách!")
            return

        if messagebox.askyesno("Xác Nhận", f"Bạn có chắc muốn tắt âm tất cả thành viên trong phòng '{self.selected_room_code}'?"):
            if self.hub:
                self.run_coro(self.hub.admin_mute_room(self.selected_room_code))

    def on_disband_room(self):
        """Giải tán / Đóng phòng đang chọn."""
        if not self.selected_room_code:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một phòng họp trong danh sách!")
            return

        if self.selected_room_code == 'seminar-network-lab':
            messagebox.showinfo("Thông Báo", "Phòng 'seminar-network-lab' là phòng họp mặc định của hệ thống, không thể xóa.")
            return

        if messagebox.askyesno("Xác Nhận Đóng Phòng", f"Bạn có chắc chắn muốn giải tán và đóng phòng họp [{self.selected_room_code}]?"):
            if self.hub:
                self.run_coro(self.hub.admin_disband_room(self.selected_room_code))
            else:
                room_manager.delete_room(self.selected_room_code)
                self.selected_room_code = "seminar-network-lab"
                self.refresh_all_data()

    # ─────────────────────────────────────────────────────────────────
    # THAO TÁC THÀNH VIÊN (PARTICIPANT CONTROLS)
    # ─────────────────────────────────────────────────────────────────
    def _get_selected_member_id(self):
        sel = self.tree_members.selection()
        if not sel:
            return None
        values = self.tree_members.item(sel[0])['values']
        return int(values[0]) if values else None

    def on_toggle_mute_client(self):
        cid = self._get_selected_member_id()
        if not cid:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một thành viên trong danh sách!")
            return

        if self.hub:
            self.run_coro(self.hub.admin_toggle_mute_client(cid))

    def on_kick_client(self):
        cid = self._get_selected_member_id()
        if not cid:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một thành viên trong danh sách!")
            return

        if messagebox.askyesno("Xác Nhận Kích", f"Bạn có chắc chắn muốn ngắt kết nối Client #{cid} khỏi phòng?"):
            if self.hub:
                self.run_coro(self.hub.admin_kick(cid, reason="Quản trị viên ngắt kết nối."))

    def on_whisper_client(self):
        cid = self._get_selected_member_id()
        if not cid:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một thành viên trong danh sách!")
            return

        # Modal nhập tin nhắn riêng
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Gửi tin nhắn riêng tới #{cid}")
        dlg.geometry("480x280")
        dlg.resizable(False, False)
        dlg.configure(bg=self.COLOR_APP_BG)
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(
            dlg, text=f"Tin nhắn riêng tới Client #{cid}:",
            font=self.FONT_SECTION, bg=self.COLOR_APP_BG, fg=self.COLOR_TEXT
        ).pack(anchor=tk.W, padx=22, pady=(18, 8))

        ent_msg = scrolledtext.ScrolledText(
            dlg, height=5, font=self.FONT_BODY, relief=tk.SOLID, bd=1,
            highlightbackground=self.COLOR_BORDER, highlightthickness=1
        )
        ent_msg.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 12))

        def do_send():
            txt = ent_msg.get("1.0", tk.END).strip()
            if not txt:
                return
            if self.hub:
                self.run_coro(self.hub.admin_whisper(cid, txt))
            dlg.destroy()
            messagebox.showinfo("Thành Công", f"Đã gửi tin nhắn riêng tới Client #{cid}!")

        btn_box = tk.Frame(dlg, bg=self.COLOR_APP_BG, padx=22, pady=12)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Gửi tin nhắn", style="Primary.TButton", command=do_send).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Đóng", style="Secondary.TButton", command=dlg.destroy).pack(side=tk.RIGHT, padx=4)

    def on_kick_from_all_tab(self):
        sel = self.tree_all_clients.selection()
        if not sel:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một Client trong danh sách!")
            return
        cid = int(self.tree_all_clients.item(sel[0])['values'][0])
        if messagebox.askyesno("Xác Nhận Kích", f"Bạn có chắc muốn ngắt kết nối Client #{cid}?"):
            if self.hub:
                self.run_coro(self.hub.admin_kick(cid, reason="Quản trị viên ngắt kết nối."))

    def on_mute_from_all_tab(self):
        sel = self.tree_all_clients.selection()
        if not sel:
            messagebox.showwarning("Cảnh Báo", "Vui lòng chọn một Client trong danh sách!")
            return
        cid = int(self.tree_all_clients.item(sel[0])['values'][0])
        if self.hub:
            self.run_coro(self.hub.admin_toggle_mute_client(cid))

    # ─────────────────────────────────────────────────────────────────
    # PHÁT THÔNG BÁO HỆ THỐNG
    # ─────────────────────────────────────────────────────────────────
    def on_send_broadcast(self):
        text = self.txt_broadcast_msg.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Cảnh Báo", "Vui lòng nhập nội dung thông báo!")
            return

        target_selection = self.combo_broadcast_target.get()

        if "Toàn bộ" in target_selection:
            if self.hub:
                self.run_coro(self.hub.admin_broadcast(text))
            messagebox.showinfo("Thành Công", "Đã phát thông báo tới tất cả các phòng họp trên hệ thống!")
        else:
            # Phát tới phòng cụ thể
            # Format: 'Phòng: code - title'
            try:
                room_code = target_selection.split(" - ")[0].replace("Phòng: ", "").strip()
                if self.hub:
                    self.run_coro(self.hub.admin_broadcast_to_room(room_code, text))
                messagebox.showinfo("Thành Công", f"Đã gửi thông báo tới phòng [{room_code}]!")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể gửi thông báo: {e}")

        self.txt_broadcast_msg.delete("1.0", tk.END)

    # ─────────────────────────────────────────────────────────────────
    # TIỆN ÍCH NHẬT KÝ & KHỞI CHẠY CLIENT
    # ─────────────────────────────────────────────────────────────────
    def clear_logs(self):
        self.txt_logs.delete("1.0", tk.END)

    def export_logs(self):
        content = self.txt_logs.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Thông Báo", "Chưa có nhật ký nào để xuất file.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Text Log File", "*.log"), ("All Files", "*.*")],
            title="Lưu Nhật Ký Hoạt Động Server"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Thành Công", f"Đã lưu nhật ký vào:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def open_desktop_app(self):
        """Mở nhanh cửa sổ ứng dụng Desktop Meet Client."""
        run_app_py = os.path.join(BASE_DIR, "run_app.py")
        subprocess.Popen([sys.executable, run_app_py])

    def on_closing(self):
        """Xử lý khi người dùng nhấn nút X đóng cửa sổ."""
        if self.is_running:
            if messagebox.askokcancel("Thoát", "Máy chủ đang chạy. Bạn có chắc muốn dừng máy chủ và đóng giao diện?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    app = ServerGUI()
    app.run()


if __name__ == '__main__':
    main()
