"""以前台进程运行科研工作台本机服务，供开发和真实浏览器 QA 使用。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.script.workbench_host import (
    PREFERRED_PORT,
    create_workbench_server,
    workbench_html_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="运行爱弥斯科研工作台本机服务")
    parser.add_argument("--port", type=int, default=PREFERRED_PORT)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port 必须在 1 到 65535 之间")

    html = workbench_html_path()
    server = create_workbench_server(
        html.parent,
        preferred_port=args.port,
        allow_fallback=False,
    )
    url = f"http://127.0.0.1:{args.port}/{html.name}"
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
