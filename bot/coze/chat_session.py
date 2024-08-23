import uuid
from common.log import logger

from channel.chat_message import ChatMessage

chat_map = {}


def get_chat(chat_id):
    global chat_map
    return chat_map.get(chat_id)


def load_chat_by_message(group_id, user_id):
    key = "{}-{}"
    if group_id is None:
        key = key.format("USER", user_id)
    else:
        key = key.format(group_id, user_id)
    if key in chat_map:
        chat = chat_map[key]
        logger.info("获取到会话: {}".format(chat))
        return chat
    else:
        return ChatSession(key, group_id, user_id)


class ChatSession(object):
    user_id = None
    chat_id = None
    messages = []
    work_order = None

    def __init__(self, chat_key, group_id, user_id):
        global chat_map
        self.user_id = user_id
        self.group_id = group_id
        self.chat_id = uuid.uuid4()
        chat_map[chat_key] = self

    def __str__(self):
        for message in self.messages:
            if isinstance(message, ReplyMessage):
                logger.info("回复: {}".format(message.content))
            else:
                logger.info("{}发送: {}".format(message.from_user_nickname, message.content))
        return ""

    def add_message(self, message: ChatMessage):
        self.messages.append(message)


class ReplyMessage(ChatMessage):

    chat_id = None
    to_user_id = None
    content = None

    def __init__(self, chat_id, to_user_id, content, _rawmsg):
        super().__init__(_rawmsg)
        self.chat_id = chat_id
        self.to_user_id = to_user_id
        self.content = content

