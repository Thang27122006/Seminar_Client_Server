import json
from config import ENCODING

MSG_JOIN = 'JOIN'      
MSG_MSG = 'MSG'         
MSG_PRIVATE = 'PRIVATE' 
MSG_QUIT = 'QUIT'       

MSG_WELCOME = 'WELCOME'         
MSG_SYSTEM = 'SYSTEM'           
MSG_ERROR = 'ERROR'             
MSG_ONLINE_LIST = 'ONLINE_LIST' 

def create_message(msg_type, data):
    message = {
        "type": msg_type,
        "data": data
    }
    return json.dumps(message, ensure_ascii=False) + '\n'


def parse_message(raw_data):
    try:
        message = json.loads(raw_data.strip())

        if 'type' not in message or 'data' not in message:
            return None
        return message

    except json.JSONDecodeError:
        return None

def encode_message(msg_type, data):
    return create_message(msg_type, data).encode(ENCODING)


def decode_messages(raw_bytes):
    try:
        text = raw_bytes.decode(ENCODING)
    except UnicodeDecodeError:
        return []

    messages = []

    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if line:  # Bỏ qua dòng trống
            msg = parse_message(line)
            if msg is not None:
                messages.append(msg)

    return messages
