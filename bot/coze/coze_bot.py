# encoding:utf-8
import json
import time
import os
import requests
from numpy.array_api import empty

from bot.bot import Bot
from bot.coze import chat_session
from utils.redis_client import RedisClient
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from bot.coze.chat_session import ChatSession, ReplyMessage
from requests_toolbelt import MultipartEncoder

start_chat_url = "https://www.coze.cn/v3/chat"
retrieve_chat_info_url = "https://www.coze.cn/v3/chat/retrieve"
message_list_url = "https://www.coze.cn/v3/chat/message/list"
feishu_bitable_token = "Jt1ob3uoQaddGhsESiFckV1cnAf"
feishu_bitable_table_id = "tblK8whhkM9hBYD5"
feishu_bitable_add_record_url = ("https://open.feishu.cn/open-apis/bitable/v1/apps/{}/tables/{}/records"
                                 .format(feishu_bitable_token, feishu_bitable_table_id))
feishu_bitable_modify_record_url = ("https://open.feishu.cn/open-apis/bitable/v1/apps/{}/tables/{}/records/{}"
                                    .format(feishu_bitable_token, feishu_bitable_table_id, "{}"))
feishu_bitable_query_record_url = ("https://open.feishu.cn/open-apis/bitable/v1/apps/{}/tables/{}/records/search"
                                   .format(feishu_bitable_token, feishu_bitable_table_id))
feishu_upload_medias_url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
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

redis_client = RedisClient()
chats = {}


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


def get_tenant_access_token():
    tenant_access_token = redis_client.get_str("FEISHU_TENANT_ACCESS_TOKEN")
    if tenant_access_token is None:
        response = requests.post(feishu_access_token_url, headers={"Content-Type": "application/json;charset=utf-8"},
                                 json={"app_id": feishu_bot_app_id, "app_secret": feishu_bot_app_secret})
        logger.info("[飞快]获取令牌:{}".format(response))
        if response.json().get('code') == 0:
            access_token = response.json().get("tenant_access_token")
            if access_token is None:
                raise ValueError("获取飞书接口令牌失败")
            tenant_access_token = str(access_token)
            logger.info("[飞书] 获取令牌:{}".format(tenant_access_token))
            redis_client.get_client().set("FEISHU_TENANT_ACCESS_TOKEN", tenant_access_token, 110 * 60)
        else:
            raise ValueError("获取飞书接口令牌失败, " + response.json().get('msg'))
    return str(tenant_access_token)


def upload_snapshot(file_name, file_path):
    token = get_tenant_access_token()
    request_headers = {"Authorization": "Bearer " + token}
    form = {"file_name": file_name,
            "parent_type": "bitable_image",
            "parent_node": feishu_bitable_token,
            "size": str(os.path.getsize(file_path)),
            "file": (open(file_path, 'rb'))}
    multi_form = MultipartEncoder(form)
    request_headers['Content-Type'] = multi_form.content_type
    response = requests.post(feishu_upload_medias_url,
                             headers=request_headers,
                             data=multi_form)
    if response.json().get("code") == 0:
        file_token = response.json().get("data").get("file_token")
        logger.info("[飞书] 上传截图成功, {}".format(file_token))
        return file_token
    else:
        raise Exception("[飞书] 上传截图失败, " + response.json().get("msg"))


def record_question(questioner, shop_name, question):
    logger.info("[飞书] 记录问题, {},  {}, {}".format(questioner, shop_name, question))
    token = get_tenant_access_token()
    logger.info("[飞书] 获取访问令牌:{}".format(token))
    record = {
        "中心": shop_name,
        "操作人登入账号": questioner,
        "问题描述": question
    }
    request_headers = {"Authorization": "Bearer " + token,
                       "Content-Type": "application/json; charset=utf-8"}
    logger.info("[飞书] 新增记录请求headers:{}".format(request_headers))
    response = requests.post(feishu_bitable_add_record_url,
                             headers=request_headers,
                             json={"fields": record})
    if response.json().get("code") == 0:
        record_id = response.json().get("data").get("record").get("record_id")
        record = query_record(record_id)
        logger.info("[飞书] 新增记录成功, {}".format(record))
        return record
    else:
        raise Exception("新增记录失败, " + response.json().get("msg"))


def query_record(record_id=None, page_token=None, create_time=None, user_name=None):
    token = get_tenant_access_token()
    request_headers = {"Authorization": "Bearer " + token,
                       "Content-Type": "application/json; charset=utf-8"}
    sort = [{
        "field_name": "工单编号",
        "desc": True
    }]
    json_data = {"sort": sort}
    if create_time is not None:
        json_data["filter"] = {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "创建时间",
                    "operator": "is",
                    "value": [
                        "ExactDate",
                        create_time
                    ]
                }
            ]
        }
    if create_time is None and user_name is not None:
        json_data["filter"] = {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "操作人登入账号",
                    "operator": "is",
                    "value": [
                        user_name
                    ]
                }
            ]
        }
    response = requests.post(feishu_bitable_query_record_url + "?page_size=10" +
                             ("&page_token=" + page_token if page_token is not None else ""),
                             headers=request_headers,
                             json=json_data)
    if response.json().get("code") == 0:
        records = response.json().get("data").get("items")
        if record_id is not None:
            for record in records:
                if record.get("record_id") == record_id:
                    return record
            if response.json().get("data").get("has_more"):
                return query_record(record_id, response.json().get("data").get("page_token"))
            else:
                return None
        elif records is None or not records:
            return None
        else:
            return records[0]
    else:
        raise Exception("查询记录失败, " + response.json().get("msg"))


def replenish_snapshot_of_question(work_order_id, snapshot):
    token = get_tenant_access_token()
    logger.info("[飞书] 获取访问令牌:{}".format(token))
    request_headers = {"Authorization": "Bearer " + token,
                       "Content-Type": "application/json; charset=utf-8"}
    logger.info("截图消息:{}".format(snapshot))
    snapshot.prepare()
    file_token = upload_snapshot("test.jpg", snapshot.content)
    response = requests.put(feishu_bitable_modify_record_url.format(work_order_id),
                            headers=request_headers,
                            json={"fields": {
                                "问题附件": [{"file_token": file_token}]
                            }})
    logger.info("[飞书] 更新记录结果:{}".format(response.json()))
    if response.json().get("code") == 0:
        logger.info("[飞书] 更新记录成功}")
        return Reply(ReplyType.TEXT, "小助手已记录该图片, 如果还有其它信息您可以继续补充")
    else:
        raise Exception("新增记录失败, " + response.json().get("msg"))


def get_last_snapshot_message(chat: ChatSession):
    for message in chat.messages:
        if message.ctype == ContextType.IMAGE:
            return message
    return None


class CozeBot(Bot):
    def __init__(self):
        super().__init__()

    def reply(self, query, context=None):
        logger.info("[COZE] 收到消息={}".format(query))
        chat_message = context.get('msg')
        is_group = chat_message.is_group
        data = {
            "bot_id": "7404342147061055507",
            "stream": False,
            "auto_save_history": True,
            "additional_messages": []
        }
        if is_group:
            group_id = chat_message.from_user_id
            user_id = chat_message.actual_user_id
            user_name = chat_message.actual_user_nickname
            shop_name = chat_message.from_user_nickname
        else:
            group_id = None
            user_id = chat_message.from_user_id
            user_name = chat_message.from_user_nickname
            shop_name = None
        questioner = user_name
        chat = chat_session.load_chat_by_message(group_id, user_id)
        chat.add_message(chat_message)
        if context.type == ContextType.TEXT:
            logger.info("[COZE] query={}".format(query))
            reply = None
            data["user_id"] = user_id
            for message in chat.messages:
                data["additional_messages"].append({
                    "content": message.content,
                    "content_type": "text",
                    "role": "bot" if isinstance(message, ReplyMessage) else "user"
                })

            logger.info("对话记录：{}".format(data["additional_messages"]))
            response = requests.post(start_chat_url, headers=headers, json=data)
            if response.json()['code'] == 0:
                reply_chat = response.json()['data']
                logger.info("[COZE] response={}".format(reply_chat))
                if reply_chat.get('status') == 'in_progress':
                    reply_result = self.check_chat_status(reply_chat.get('id'), reply_chat.get('conversation_id'))
                    if reply_result.get("c") == 2:
                        reply = Reply(ReplyType.TEXT, "您好，我是龙翊运营小助手，请留下您的问题，我会尽快处理")
                    elif reply_result.get("c") == 3:
                        reply = Reply(ReplyType.TEXT, "不好意思，小助手正在全力解决问题，暂时没有时间闲聊，如有系统问题请留下您的问题")
                    elif reply_result.get("c") == 1:
                        record = record_question(questioner, user_id, shop_name, query)
                        chat.work_order = record
                        reply = Reply(ReplyType.TEXT, "您的问题已登记，本小助手会尽快解决，请稍等, 工单编号:{}"
                                      .format(chat.work_order.get("fields").get("工单编号")))
                    elif reply_result.get("c") == 4:
                        # 获取图片消息,并将图片上传到工单
                        message = get_last_snapshot_message(chat)
                        reply = replenish_snapshot_of_question(chat.work_order.get("record_id"), message)
                    elif reply_result.get("c") == 6:
                        # 查询进度
                        if chat.work_order is None:
                            record = query_record(None, None, None, user_name)
                            if record is not None:
                                chat.work_order = record
                        else:
                            record = query_record(chat.work_order.get("record_id"), None,
                                                  chat.work_order.get("fields").get("创建时间"))
                        if record is None:
                            reply = Reply(ReplyType.TEXT, "报错，小助手没有找到您的工单，麻烦您把您的问题再发一遍")
                        else:
                            fields = record.get("fields")
                            status = None
                            charger = None
                            solution = None
                            if "处理状态" in fields:
                                status = fields.get("处理状态")[0].get("text")
                            if "工单负责人" in fields:
                                charger = fields.get("工单负责人")[0].get("name")
                            if "解决" in fields:
                                solution = fields.get("解决")[0].get("text")
                            reply = Reply(ReplyType.TEXT, ("当前问题处理状态：" + (status if status is not None else "处理中") +
                                                           ", 工单负责人：" + (charger if status is not None else "等待分配") +
                                                           ", 处理意见：" + (solution if solution is not None else "暂无") +
                                                           "。您也可直接联系工单负责人询问具体情况"))
                    else:
                        reply = Reply(ReplyType.TEXT, "不好意思，我不知道您在说什么，请换个方式提问")
            else:
                logger.info("[COZE] response({})={}".format(response.json()['code'], response.json()['msg']))
                reply = Reply(ReplyType.TEXT, "小助手头有点昏, 让我休息一下")
        elif context.type == ContextType.IMAGE:
            logger.info("[COZE] 收到图片")
            reply = Reply(ReplyType.TEXT, "收到了一张图片, 为了更快的解决问题, 请确认该图片是否与您要解决的问题有关")
        else:
            reply = Reply(ReplyType.ERROR, "小助手不支持处理{}类型的消息".format(context.type))
        chat.add_message(ReplyMessage(chat.chat_id, user_id, reply.content, None))
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


def main():
    # file_path = "D:/Projects/chatgpt-on-wechat/tmp/240823-134102.png"
    # form = {"file_name": file_path,
    #         "parent_type": "bitable_image",
    #         "size": os.path.getsize(file_path),
    #         "file": (open(file_path, 'rb'))}
    # multi_form = MultipartEncoder(form)
    record = query_record(None, None, None, "Joey")
    logger.info("查询结果:{}".format(record))


if __name__ == "__main__":
    main()
