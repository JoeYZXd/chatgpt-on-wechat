from common.singleton import singleton
from config import conf
from lib.itchat import web_init
from utils.redis_client import RedisClient
import requests
from common.log import logger


redis_client = RedisClient()
feishu_bot_app_id = conf().get('feishu_app_id')
feishu_bot_app_secret = conf().get('feishu_app_secret')
feishu_token = conf().get('feishu_token')
feishu_access_token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"


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


def get_json_header():
    common_header = get_common_header()
    common_header["Content-Type"] = "application/json; charset=utf-8"


def get_common_header():
    return {
        "Authorization": "Bearer " + get_tenant_access_token()
    }


def post_json(data):
    return


class question_record(object):
    work_order_id = None
    question = None
    solution = None
    row = None
    column = None

    def __init__(self, work_order_id, question, solution):
        super()
        self.work_order_id = work_order_id
        self.question = question
        self.solution = solution



@singleton
class work_book_api(object):

    append_record_url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/:spreadsheetToken/values_append"
    find_cell_url = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/:spreadsheet_token/sheets/:sheet_id/find"
    sheet_token = "Z04Xsmkfkh3NrVt8ftzciOydnGY"
    sheet_id = "73f722"
    max_row_index = None
    max_row_key = "fei_shu_sheet_{}_max_row".format(sheet_id)

    def __init__(self):
        super()
        if redis_client.get_client().exists(self.max_row_key):
            max_row_index = redis_client.get_str(self.max_row_key)
        else:
            max_row_index = self.get_max_row_index()

    def get_row_by_work_order_id(self, work_order_id):
        url = self.find_cell_url.format(self.sheet_token, self.sheet_id)


    def append_record(self, sheet_token, record:question_record):
        url = self.append_record_url.format("P2htwbSmwiFkjJkQTExcbZAbnhf")






