from flask import Flask, request

app = Flask(__name__)


@app.route('/')
def home():
    return "hello, world"


def run_server():
    app.run(host="0.0.0.0", port=5000)

