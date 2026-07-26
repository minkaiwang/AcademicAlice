本目录存放随版本受控的本地辅助服务。

- `yuanbao-free-api/`：随爱弥斯源码 / 发行包交付的元宝 Web 本地中转服务目录。
- 安装器和桌宠不会再下载浮动 `main.zip`，也不会解压未经 SHA256 固定的外部服务包。
- 若该目录缺少 `app.py` 或 `requirements.txt`，说明发行包不完整，应重新获取正式包。
- 当 AI 配置启用 `YuanBao-Free-API` 且接口地址指向本地 `127.0.0.1:8000` 时，桌宠启动时会自动尝试拉起该服务。
- 首次启动成功后，会在 `logs/yuanbao_free_api_qrcode.png` 生成登录二维码图片。
- 若启动失败，请查看 `logs/yuanbao_free_api_launcher.log`。
