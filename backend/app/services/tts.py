# https://developer.aliyun.com/article/1612744
#
import os
import shutil
import uuid

# 这个要用/ 结尾
from datetime import datetime
from pathlib import Path

from gradio_client import Client

from app.core.config import settings


def generate_unique_filename(extension=".mp3"):
    """生成带日期的唯一文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]  # 使用UUID的前8位
    return f"audio_{timestamp}_{unique_id}{extension}"


def test_bk_tts():
    content = "这是一个测试"
    audio_url = bk_tts(content)
    print(audio_url)


def bk_tts(content, sound="中文女", seed=0) -> str | None:
    cosyvoice_endpoint = settings.TTS_ENDPOINT
    client = Client(cosyvoice_endpoint)
    result = client.predict(
        _sound_radio=sound,
        _synthetic_input_textbox=content,
        _seed=seed,
        api_name="/generate_audio",
    )
    # result 是返回的本地音频地址
    # 把result 保存到当前的目录下
    audio_filename = generate_unique_filename()
    current_dir = Path(__file__).parent.parent
    audio_file = Path.joinpath(current_dir, "static", "audio", audio_filename)
    shutil.copy(result, audio_file)
    # 删除原始的 音频
    os.remove(result)
    return (
        settings.STATIC_DOMAIN
        + "/"
        + settings.STATIC_PREFIX
        + "/audio/"
        + audio_filename
    )
