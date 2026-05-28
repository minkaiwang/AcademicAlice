"""产品显示名与标语（零第三方依赖）。

供 `install/install_deps.py`、以及任何在导入 `config` 包之前需要展示名的代码使用。
应用内其他模块可 `from app_brand import APP_DISPLAY_NAME` 或从 `config.version_info` 再导出读取。
"""

APP_DISPLAY_NAME = "爱弥斯"
APP_DISPLAY_NAME_EN = "Aemeath"
APP_TAGLINE = "学术桌面助手"

# 托盘「关注作者」打开的 B 站空间（原作者授权二创后可指向当前维护者）
AUTHOR_BILIBILI_SPACE_URL = (
    "https://space.bilibili.com/10845469?spm_id_from=333.788.0.0"
)
