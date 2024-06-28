import requests
import json
from constants import DATA_PATH
import os
import time

testPath = os.path.join(DATA_PATH, "omo/test")

def get_access_token():
    """
    使用 API Key，Secret Key 获取access_token，替换下列示例中的应用API Key、应用Secret Key
    """

    url = "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=TZ4vStFOpahRrfn1HB4appnc&client_secret=0bvOIvgn4UaqFUH1L6II9LhUhMAatMPU"

    payload = json.dumps("")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")

def ie_by_ernie(content):

    question1 = f"你是一个自然语言处理专业机器人，你需要从我给出的内容中抽取[逆回购、MLF、央行票据的交易情况]并用过[josn]的格式展示结果，不需要展示空结果。接下来你需要抽取的内容是：[{content}]"
    question2 = f"你是一个自然语言处理专业机器人，你需要从我给出的内容中抽取[逆回购、正回购、MLF、央行票据]，并使用[json]格式直接输出结果，结果中不需要包括未提供的信息。需要抽取的内容是：[{content}]"

    url = (
        "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-speed-128k?access_token="
        + get_access_token()
    )

    payload = json.dumps({"messages": [{"role": "user", "content": question2}]})
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)
    resJson = response.json()

    print(resJson)
    if resJson['result']:
        f = open(os.path.join(testPath, f"{time.time()}.txt"), "w", encoding="utf-8")
        f.write(f'Q: {question2}\n\nA: {resJson["result"]}')
        f.close()
        return resJson
    else:
        return None
