# Vendored dependency

## pyncm 1.8.1

- 文件：`pyncm-1.8.1-py3-none-any.whl`
- 用途：网易云音乐 API 适配；上游包索引不可用时保证新环境仍可安装
- 原发布元数据：PyPI `pyncm==1.8.1`，主页
  `https://github.com/greats3an/pyncm`（曾重定向至
  `https://github.com/mos9527/pyncm`）
- 许可证：Apache License 2.0；许可证正文包含于 wheel 的
  `pyncm-1.8.1.dist-info/LICENSE`，同版通用条款亦见根目录
  `LICENSE-CODE`
- wheel SHA256：
  `a1798e9ff9007723d0a34b4d61b51b385b5bedb6caac6e04ce5572d00193183c`

2026-07-26 核验记录：PyPI 项目页仍显示 1.8.1（2025-10-18），但
`/simple/pyncm/` 与上游 Git 仓库均返回 404。wheel 由本机此前从
PyPI 安装的 1.8.1 纯 Python 副本重打；重打前按原
`pyncm-1.8.1.dist-info/RECORD` 校验 33 个源文件及元数据，缺失 0、
哈希不符 0。未包含 `demos/`、入口 EXE 或 `__pycache__`。
