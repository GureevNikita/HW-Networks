import re

import requests as rqst
from requests.exceptions import ReadTimeout, ConnectionError, ChunkedEncodingError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

base_url = "http://hw1.alexbers.com"
token = "bd5edd3c586220ba177a2f4ab4f4027a"

sess = rqst.Session()
sess.cookies.update({"user": token})


def parse(response_text):

    result = {
        "url": base_url,
        "method": "POST" if ("POST-запрос" in response_text or "Загрузите файлы" in response_text) else "GET"
    }

    # STEP
    step_match = re.search(r"<h1>Шаг #(\d+) \(из множества\)</h1>", response_text)
    if step_match:
        result["step"] = step_match.group(1)
    else:
        result["step"] = None


    # ADDRESS
    addr_match = re.search(r"по адресу\s*<code>([^<]+)</code>", response_text) or \
                 re.search(r"""Перейдите\s+по\s*<a\s+href=["']([^"']+)["']""", response_text, flags=re.IGNORECASE)
    if addr_match:
        result["url"] += addr_match.group(1)

    # SECRET KEY
    key_match = re.search(r"Секретный ключ:\s*<b><code>([^<]+)</code></b>", response_text)
    if key_match:
        result["secret_key"] = key_match.group(1)

    table_keywords = {
        "cookies": r"cookie",
        "data": r"данные формы",
        "headers": r"следующие заголовки",
        "files": r"Загрузите файлы",
        "params": r"параметры запроса"
    }

    row_pattern = r"<td><code>([^<]+)</code></td>\s*<td><code>([^<]+)</code></td>"

    for key, keyword in table_keywords.items():
        table_match = re.search(fr"{keyword}.*?(<table.*?>.*?</table>)", response_text, flags=re.I | re.S)
        if table_match:
            result[key] = dict(re.findall(row_pattern, table_match.group(1)))
        else:
            result[key] = {}

    result["cookies"]["user"] = token
    result["headers"]["Connection"] = "Close"

    return result


parsed_html_request = {
    "step": 0,
    "method": "GET",
    "url": base_url,
    "params": {},
    "data": {},
    "files": {},
    "cookies": {"user": token},
    "headers": {"Connection": "Close"},
    "secret_key" : None
}


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ReadTimeout, ConnectionError, ChunkedEncodingError)),
)
def make_request(parsed_html_request, session):
    kwargs = {
        key: parsed_html_request[key]
        for key in ("url", "params", "data", "files", "cookies", "headers")
        if parsed_html_request.get(key) is not None
    }

    kwargs["timeout"] = (10, 60)

    response = session.request(method=parsed_html_request["method"], **kwargs)
    response.encoding = "utf-8"
    session.close()

    return response



prev_step = None

while True:
    response = make_request(parsed_html_request, sess)
    parsed_html_request = parse(response.text)
    print(parsed_html_request.get("step"))
    if parsed_html_request.get("secret_key") is not None:
        print("secret key is: ",parsed_html_request["secret_key"])
        break


