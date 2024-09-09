from flask import Flask, request
from common.log import logger

app = Flask(__name__)


@app.route('/')
def home():
    return "hello, world"

@app.route('/update-record', methods=["POST"])
def update_record():
    work_order_id = request.args.get("work_order_id")
    logger.info("收到更新请求, 工单号:{}".format(work_order_id))
    return {}


def run_server():
    app.run(host="0.0.0.0", port=5000)

