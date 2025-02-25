import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings

one_api_url = (
    settings.ONE_API_BASE_URL + "/chat/completions"
)  ##|| "http://127.0.0.1:3000/v1"
one_token = settings.ONE_TOKEN


def get_content_parse_system_prompt() -> str:
    return """ 你是一个文档处理专家，你能高效地处理markdown格式的文本。并且能去除文版本中不方便转化为语音的内容。
    一些不方便转化为语音的内容包括：图片,超链接，代码块，表格等。
    去除这些内容后，你还需要对剩余的文本进行分析，如果出现语句不通顺，你需要对其进行修改。
    接着对修改后的文本进行打标签，如：新闻，科技，教育等，标签数量不要超过5个。
    最后生成摘要，并按照以下json格式返回：
    {
        "tags":["科技","教育"],
        "abstract":"这是一个科学技术在高等教育中的应用的案例",
        "content":"如何将科学技术应用到高等教育中，这是一个很好的案例。....."
    }
    【注意】：不需要对文本进行翻译，只需要对文本进行处理，按照格式返回即可，如果原文是英文，返回的content也要是英文。
"""


def get_tag_aggregate_system_prompt() -> str:
    return """ 你是一个文档处理专家，你能高效地处理markdown格式的文本。根据用户提供给你的多条数据，总结分析，最后生成一篇流畅的文章。并对这个文章打标签，如：新闻，科技，教育等，标签数量不要超过5个。
    最后生成摘要。 并按照以下json格式返回标签（tags)、摘要（asbtract）、文章内容（content）：
    {
        "tags":["科技","教育"],
        "abstract":"这是一个科学技术在高等教育中的应用的案例",
        "content":"如何将科学技术应用到高等教育中，这是一个很好的案例。....."
    }
    【注意】：不需要对文本进行翻译，只需要对文本进行处理，按照格式返回即可，如果原文是英文，返回的content也要是英文。
"""


def deal_content_parse_ret(answer: str) -> dict:
    """
    Parse the LLM response string containing JSON data into a dictionary.

    Args:
        answer (str): The string response from LLM containing JSON data

    Returns:
        dict: A dictionary with keys 'tags', 'abstract', and 'content'.
              Returns empty dict if parsing fails.

    Example input:
        {
            "tags": ["科技", "教育"],
            "abstract": "这是一个科学技术在高等教育中的应用的案例",
            "content": "如何将科学技术应用到高等教育中，这是一个很好的案例....."
        }
    """

    try:
        # Find the first '{' and last '}' in the string
        start = answer.find("{")
        end = answer.rfind("}")

        if start != -1 and end != -1:
            # Extract the JSON string
            json_str = answer[start : end + 1]
            # Parse JSON string to dict
            result = json.loads(json_str)

            # Validate required keys
            required_keys = ["tags", "abstract", "content"]
            if all(key in result for key in required_keys):
                return result

        return {}

    except json.JSONDecodeError:
        return {}


def request_ai(model, query, system_prompt="", chat_url=one_api_url, token=one_token):
    # 创建一个Session对象
    session = requests.Session()

    # 配置重试机制
    retry = Retry(
        total=3,  # 总共重试次数
        backoff_factor=1,  # 延迟因子
        status_forcelist=[500, 502, 503, 504, 429, 413],  # 针对这些状态码进行重试
        # allowed_methods=["POST", "OPTIONS", "GET"]  # 仅针对这些HTTP方法重试
    )

    # 将重试机制应用到Session中
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 设置headers
    headers = {
        "Content-Type": "application/json",  # 请求体类型（可以根据需要设置）
        "Authorization": f"Bearer {token}",  # 示例授权头
    }

    messages = []
    if system_prompt != "":
        messages.append(
            {
                "role": "user" if model.startswith("o1") else "system",
                "content": system_prompt,
            }
        )
    messages.append({"role": "user", "content": query})
    # 设置请求数据
    data = {
        "model": model,
        "messages": messages,
    }

    # 发送POST请求
    start_time = time.time()
    status_code = 200
    try:
        response = session.post(chat_url, json=data, headers=headers)
        end_time = time.time()
        # response.raise_for_status()  # 如果响应状态码是4xx/5xx会抛出异常
        status_code = response.status_code
        resp = response.json()
        answer = ""  # 当无法获取时的备用值
        if resp and "choices" in resp and resp["choices"]:
            answer = resp["choices"][0]["message"].get("content", "")  #
        if status_code == 200 and len(answer) > 0:
            return {
                "status_code": status_code,
                "data": response.json(),  # 打印返回的内容
                "milliseconds": int((end_time - start_time) * 1000),
                "answer": answer,
            }
        else:
            return {
                "status_code": status_code,
                "error": response.json(),  # 打印返回的JSON内容
                "milliseconds": int((end_time - start_time) * 1000),
            }
    except Exception as e:
        end_time = time.time()
        return {
            "status_code": status_code,
            "error": {"message": str(e)},
            "milliseconds": int((end_time - start_time) * 1000),
        }


if __name__ == "__main__":
    ret = request_ai(
        "deepseek-chat",
        "你好,你是谁？",
        "sk-si8aCMok1EVQ6NzI48C69bA3464540909dE6FcF9148287B9",
        "",
    )
    print(ret)
    print(ret["data"]["choices"][0]["message"]["content"])
