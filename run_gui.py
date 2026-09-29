import sys
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from client.gui import ChatGUI


def main():
    app = ChatGUI()
    app.run()


if __name__ == '__main__':
    main()
