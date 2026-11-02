import sys
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from client.client import ChatClient


def main():
    client = ChatClient()
    client.connect()


if __name__ == '__main__':
    main()
