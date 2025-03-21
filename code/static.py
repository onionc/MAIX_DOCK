import os
import uuid
from flask import Flask, request, jsonify

# 配置服务器
UPLOAD_FOLDER = "static/uploads"  # 图片存储目录
BASE_URL = "http://127.0.0.1:9001/"  # 服务器访问地址

# 创建目录（如果不存在）
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化 Flask
app = Flask(__name__)


@app.route("/upload", methods=["POST"])
def upload_image():
    """接收图片并存储到静态目录"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}.jpg"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # 保存图片
    file.save(file_path)

    # 返回访问 URL
    file_url = f"{BASE_URL}{file_path}"
    return jsonify({"url": file_url})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
