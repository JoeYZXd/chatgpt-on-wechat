from flask import Flask, request
from common.log import logger

app = Flask(__name__)


@app.route('/')
def home():
    return "hello, world"

@app.route('/update-record', methods=["POST"])
def update_record():
    logger.info("收到更新请求".format(request))


def run_server():
    app.run(host="0.0.0.0", port=5000)

