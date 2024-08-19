# encoding:utf-8
import json
import time
import os
import base64
import requests
from bot.bot import Bot
from bot.session_manager import SessionManager
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf, load_config
from common import memory, utils

start_chat_url = "https://www.coze.cn/v3/chat"
retrieve_chat_info_url = "https://www.coze.cn/v3/chat/retrieve"
message_list_url = "https://www.coze.cn/v3/chat/message/list"
feishu_bitable_add_record_url = "https://open.feishu.cn/open-apis/bitable/v1/apps/{}/tables/tblK8whhkM9hBYD5/records"
feishu_bitable_app_token = "Jt1ob3uoQaddGhsESiFckV1cnAf"
feishu_bitable_table_id = "tblK8whhkM9hBYD5"
feishu_bot_app_id = "cli_a634401cb7fc500d"
feishu_bot_app_secret = "HispFV8dn0tW24IUosYoFdfko4T7sToj"
feishu_access_token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"


headers = {
    'authorization': 'Bearer pat_xjythCC1bvpqKtuSggwNPkb5XeItpk4NbghWA1PtFIhK6dMxhGRvIGy2FqF82QNe',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Host': 'api.coze.cn',
    'Connection': 'keep-alive'
}

data = {
    "bot_id": "7404342147061055507",
    "stream": False,
    "auto_save_history": True,
    "additional_messages": []
}


def list_chat_message(chat_id, conversation_id):
    response = requests.get(message_list_url, headers=headers,
                            params={"conversation_id": conversation_id, "chat_id": chat_id})
    if response.json()['code'] == 0:
        message_list = response.json()['data']
        for message in message_list:
            if message.get('type') == 'answer':
                if message.get('content') is not None:
                    logger.info("[COZE] 工作流返回结果:{}".format(message))
                    return json.loads(message.get('content'))
        raise ValueError("消息列表内不存在回答")
    else:
        raise ValueError('获取消息列表失败')


def request_feishu_access_token():
    response = requests.post(feishu_access_token_url, headers={"Content-Type": "application/json;charset=utf-8"},
                             data={"app_id": feishu_bot_app_id, "app_secret": feishu_bot_app_secret})
    if response.json().get('code') == 0:
        return response.json().get("tenant_access_token")


def record_question(questioner, shop_name, question):
    logger.info("[飞书] 记录问题, {},  {}, {}".format(questioner, shop_name, question))
    token = request_feishu_access_token()
    logger.info("[飞书] 获取访问令牌:{}".format(token))
    return


class CozeBot(Bot):
    def __init__(self):
        super().__init__()

    def reply(self, query, context=None):
        logger.info("[COZE] 收到消息={}".format(query))
        shop_name = context.get('msg').from_user_nickname
        questioner = context.get('msg').actual_user_nickname
        if context.type == ContextType.TEXT:
            logger.info("[COZE] query={}".format(query))
            reply = None
            data["user_id"] = context.kwargs.get("msg").from_user_id
            data["additional_messages"] = [{
                "content": query,
                "content_type": "text",
                "role": "user"
            }]

            response = requests.post(start_chat_url, headers=headers, json=data)
            if response.json()['code'] == 0:
                reply_chat = response.json()['data']
                logger.info("[COZE] response={}".format(reply_chat))
                if reply_chat.get('status') == 'in_progress':
                    reply_result = self.check_chat_status(reply_chat.get('id'), reply_chat.get('conversation_id'))
                    if reply_result.get("c") == 2:
                        return Reply(ReplyType.TEXT, "您好，我是龙翊运营小助手，请留下您的问题，我会尽快处理")
                    elif reply_result.get("c") == 3:
                        return Reply(ReplyType.TEXT, "不好意思，小助手正在全力解决问题，暂时没有时间闲聊，如有系统问题请留下您的问题")
                    elif reply_result.get("c") == 1:
                        record_question(questioner, shop_name, query)
                        return Reply(ReplyType.TEXT, "您的问题已登记，本小助手会尽快解决，请稍等")
                    else:
                        return Reply(ReplyType.TEXT, "不好意思，我不知道您在说什么，请换个方式提问")
            else:
                logger.info("[COZE] response({})={}".format(response.json()['code'], response.json()['msg']))
            return reply
        else:
            reply = Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))
            return reply

    def check_chat_status(self, chat_id, conversation_id):
        time.sleep(1)
        response = requests.get(retrieve_chat_info_url, headers=headers,
                                params={"conversation_id": conversation_id, "chat_id": chat_id})
        if response.json()['code'] == 0:
            chat_reply = response.json()['data']
            if chat_reply.get('status') == 'in_progress':
                return self.check_chat_status(chat_id, conversation_id)
            elif chat_reply.get('status') == 'completed':
                return list_chat_message(chat_id, conversation_id)
        else:
            return 'none'
