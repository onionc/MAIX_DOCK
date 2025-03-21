# coding=utf-8
import socket
import base64
import json
import os
import requests
from openai import OpenAI
import struct

# 配置 LLM API
API_KEY = "sk-xxx"  # 请替换为你的 DashScope API Key
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-vl-plus"  # 选择的 LLM 模型

# TCP 服务器配置
HOST = "0.0.0.0"
PORT = 9002
BUFFER_SIZE = 1024 * 1024  # 1MB 缓冲区

# Flask 服务器上传 API
UPLOAD_URL = "http://39.103.59.12:9001/upload"


# 初始化 OpenAI 客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def upload_image(image_data):
    """上传图片到 Flask 服务器"""
    files = {"file": ("image.jpg", image_data, "image/jpeg")}
    response = requests.post(UPLOAD_URL, files=files)

    if response.status_code == 200:
        return response.json().get("url")
    else:
        print("图片上传失败:", response.text)
        return None


def call_llm(image_url):
    """调用 LLM 处理图片"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "你是一个图片助手，用户给你输入一张图片，你用简短的语言来描述图片的物体，以特殊词“bingo!”开头，除特殊词外不能超过10个字，内容中不需要出现“图中”等字眼，只描述物体就行，比如“一个苹果”。 如果没输入图片，你就说“主人，请输入图片”"},
                        {"type": "image_url", "image_url": {"url":image_url}}
                    ]
                }
            ]
        )
        # 解析 LLM 响应
        response_data = json.loads(completion.model_dump_json())
        text_result = response_data.get("choices", [{}])[0].get("message", {}).get("content", "LLM 解析失败")
        return text_result
    except Exception as e:
        return f"LLM 调用失败: {str(e)}"

def xor_checksum(data):
    """计算 XOR 校验"""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def handle_client(conn, addr):
    """处理 TCP 连接"""
    print(f"连接来自: {addr}")

    try:
        # 超时断开
        conn.settimeout(5)
        
        # 解析协议：帧头（0XAB，0XCD），长度（4字节数据长度，小端），数据...，校验（1位异或）
        # 帧头 AB CD
        header = conn.recv(2)
        if header!=b'\xAB\xCD':
            print("协议解析：帧头错误")
            conn.sendall(b"ERROR: Invaild header")
            return
        # 长度
        data_len_bs = conn.recv(4)
        if not data_len_bs:
            print("协议解析：长度错误")
            conn.sendall(b"ERROR: Invaild len")
            return
        data_len = struct.unpack("<I", data_len_bs)[0]
        if data_len < 1:
            print("协议解析：数据为空")
            conn.sendall(b"ERROR: Empty data")
            return
        print(f"接收数据长度: {data_len} 字节")
        # 数据
        data = b""
        while len(data) < data_len:
            chunk = conn.recv(min(BUFFER_SIZE, data_len-len(data)))
            if not chunk:
                break  # 连接关闭，停止接收
            data+=chunk
        if len(data) != data_len:
            print("协议解析：数据不完整")
            conn.sendall(b"ERROR: Incomplete data")
            return
        # 校验
        check_byte = conn.recv(1)
        check = struct.unpack("<B", check_byte)[0]
        if xor_checksum(data)!=check:
            print("协议解析：校验失败 {} {}".format(xor_checksum(data), check))
            conn.sendall(b"ERROR: Check mismatch")
            return
        
        # 上传图片
        print("upload image")
        image_url = upload_image(data)
        if not image_url:
            conn.sendall(b"ERROR: Image upload failed")
            return

        print("图片 URL:", image_url)

        # 调用 LLM
        llm_result = call_llm(image_url)
        print("LLM 结果:", llm_result)

        # 返回结果
        conn.sendall(llm_result.encode())
    except socket.timeout:
        # 超时断开
        print("conn timeout")
        conn.sendall(b"ERROR: timeout")
    except Exception as e:
        print("处理失败:", e)
        conn.sendall(b"ERROR: Server error")
    finally:
        conn.close()


def start_server():
    """启动 TCP 服务器"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"TCP 服务器已启动，监听端口 {PORT}...")

        while True:
            conn, addr = server.accept()
            conn.settimeout(5)
            print(f"连接来自: {addr}")
            handle_client(conn,addr)


if __name__ == "__main__":
    start_server()

