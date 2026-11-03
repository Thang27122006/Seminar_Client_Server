#!/usr/bin/env python3
"""
Desktop Application Launcher cho Nền Tảng Google Meet & Seminar Lập Trình Mạng.
Đóng gói toàn bộ giao diện và chức năng thành một Cửa Sổ Ứng Dụng Desktop (Desktop App Window)
độc lập, không hiển thị thanh URL hoặc điều hướng trình duyệt, hoạt động như phần mềm máy tính thuần túy.
"""

import os
import sys
import time
import socket
import shutil
import platform
import subprocess
import signal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DEFAULT_PORT = 8080
DEFAULT_ROOM = "seminar-network-lab"
APP_TITLE = "Seminar Lập Trình Mạng - Google Meet Desktop App"


def is_server_running(host="127.0.0.1", port=DEFAULT_PORT):
    """Kiểm tra máy chủ backend có đang hoạt động trên cổng quy định hay không."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def start_backend_server():
    """Tự động khởi chạy máy chủ backend trong tiến trình ngầm nếu chưa chạy."""
    if is_server_running():
        return None

    run_server_script = os.path.join(BASE_DIR, "run_server.py")
    venv_python = os.path.join(BASE_DIR, ".venv", "bin", "python3")
    py_exec = venv_python if os.path.exists(venv_python) else sys.executable

    print("🚀 [DESKTOP LAUNCHER] Đang tự động khởi chạy máy chủ backend...")
    proc = subprocess.Popen(
        [py_exec, run_server_script],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Chờ máy chủ sẵn sàng (tối đa 6 giây)
    for _ in range(30):
        if is_server_running():
            print("✅ [DESKTOP LAUNCHER] Máy chủ backend đã sẵn sàng!")
            return proc
        time.sleep(0.2)

    return proc


def find_browser_binary():
    """
    Tìm kiếm trình khởi tạo cửa sổ ứng dụng Desktop (Chromium / Chrome / Edge).
    Hỗ trợ cả Linux, Windows và macOS.
    """
    system = platform.system()

    if system == "Windows":
        candidates = [
            # Microsoft Edge (Có sẵn 100% trên Windows 10/11)
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            # Google Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Brave
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

        for name in ["msedge.exe", "chrome.exe", "brave.exe"]:
            found = shutil.which(name)
            if found:
                return found

    elif system == "Darwin":  # macOS
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

    else:  # Linux
        for name in [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
            "microsoft-edge-stable",
            "brave-browser",
            "firefox"
        ]:
            found = shutil.which(name)
            if found:
                return found

    return None


def launch_desktop_app(target_url=None, width=1280, height=820):
    """
    Khởi chạy giao diện trong Cửa sổ Ứng dụng Desktop chuyên dụng (App Mode).
    Mặc định mở Trang Chủ Google Meet (Tạo cuộc họp mới / Nhập mã phòng).
    """
    if not target_url:
        target_url = f"http://127.0.0.1:{DEFAULT_PORT}/"

    # 1. Tự động kiểm tra và khởi chạy Server nếu cần
    server_process = start_backend_server()

    # 2. Tìm binary để hiển thị App Window
    browser_bin = find_browser_binary()
    if not browser_bin:
        print("❌ Không tìm thấy trình khởi chạy cửa sổ Desktop tương thích trên hệ thống.")
        print(f"👉 Vui lòng mở thủ công tại địa chỉ: {target_url}")
        return

    # 3. Tạo thư mục profile riêng biệt cho Desktop App để không xung đột với trình duyệt ngoài
    profile_dir = os.path.join(BASE_DIR, "data", "desktop_profile")
    os.makedirs(profile_dir, exist_ok=True)

    print("══════════════════════════════════════════════════════════════════════")
    print("  💻 KHỞI CHẠY CHƯƠNG TRÌNH DESKTOP (MEET DESKTOP APPLICATION)")
    print("  ► Cửa sổ ứng dụng: Standalone Native Window")
    print("  ► Đường dẫn đích:  " + target_url)
    print("  ► Bộ dựng hình:    " + os.path.basename(browser_bin))
    print("══════════════════════════════════════════════════════════════════════")

    is_firefox = "firefox" in os.path.basename(browser_bin).lower()

    if is_firefox:
        cmd = [
            browser_bin,
            "--new-window",
            target_url
        ]
    else:
        # Chromium / Chrome / Edge App Mode: Không có thanh URL, không tab, cửa sổ ứng dụng thuần
        cmd = [
            browser_bin,
            f"--app={target_url}",
            f"--user-data-dir={profile_dir}",
            f"--window-size={width},{height}",
            "--window-position=center",
            "--disable-background-networking",
            "--disable-sync",
            "--no-first-run",
            "--no-default-browser-check",
            "--autoplay-policy=no-user-gesture-required",
            "--enable-media-stream",
            "--use-fake-ui-for-media-stream",
            f"--class=SeminarMeetApp",
            f"--name={APP_TITLE}"
        ]

    try:
        app_proc = subprocess.Popen(cmd)
        app_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if server_process:
            print("\n🛑 Đang dừng máy chủ backend chạy ngầm...")
            try:
                server_process.terminate()
                server_process.wait(timeout=2)
            except Exception:
                try:
                    server_process.kill()
                except Exception:
                    pass
        print("👋 Đã đóng chương trình Desktop. Tạm biệt!")


def main():
    target_url = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg in ["--home", "home"]:
            target_url = f"http://127.0.0.1:{DEFAULT_PORT}/"
        elif arg.startswith("http://") or arg.startswith("https://"):
            target_url = arg
        elif not arg.startswith("-"):
            # Mã phòng
            target_url = f"http://127.0.0.1:{DEFAULT_PORT}/room?code={arg}"

    launch_desktop_app(target_url=target_url)


if __name__ == "__main__":
    main()
