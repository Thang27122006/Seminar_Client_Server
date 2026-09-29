import sys

# Thiết lập bảng mã UTF-8 cho console Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from server.server import ChatServer


def main():
    if '--gui' in sys.argv or '-g' in sys.argv:
        from server.gui import ServerGUI
        app = ServerGUI()
        app.run()
    else:
        server = ChatServer()
        server.start()


if __name__ == '__main__':
    main()
