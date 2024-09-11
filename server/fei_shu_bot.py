from flask import Flask, request
from common.log import logger
from bot.coze.chat_session import ChatSession, ReplyMessage, get_chats
from lib import itchat
from lib.itchat.content import *
import json

app = Flask(__name__)


@app.route('/')
def home():
    return "hello, world"

@app.route('/update-record', methods=["POST"])
def update_record():
    work_order_id = request.args.get("work_order_id")
    params = request.json
    logger.info("收到更新请求, 工单号:{}, 参数:{}".format(work_order_id, params))
    return {}

@app.route('/chats', methods=["GET"])
def load_chats():
    params = request.json
    friend_name = params.get("to_user_name")
    message = params.get("message")
    chats = get_chats()
    friends = itchat.search_friends(name=friend_name)
    itchat.instance.send(message, toUserName=friends[0]['UserName'])
    return {"size": len(chats)}

@app.route('/reply', methods=["POST"])
def manual_reply():
    return {}


def run_server():
    app.run(host="0.0.0.0", port=5000)

