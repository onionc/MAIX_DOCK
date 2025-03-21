#coding=utf-8
import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="sk-6929cd07ceeb49e2950fc6795e68e1aa",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-vl-plus",  # 此处以qwen-vl-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[
            {"role": "user","content": [
            {"type": "text","text": "你是一个图片助手，用户给你输入一张图片，你用简短的语言来描述图片的物体，以特殊词“bingo!”开头，不超过20个字。 如果没输入图片，你就说“主人，请输入图片”"},
            {"type": "image_url",
             "image_url": {"url": "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"}}
            ]}]
    )
print(completion.model_dump_json())
