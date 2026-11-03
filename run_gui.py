import sys
import os

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def main():
    if '--classic' in sys.argv or '--tkinter' in sys.argv:
        from client.gui import ChatGUI
        app = ChatGUI()
        app.run()
    else:
        from client.desktop_app import main as desktop_main
        desktop_main()


if __name__ == '__main__':
    main()
