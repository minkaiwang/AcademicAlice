"""从历史随机端口对应的浏览器 localStorage 恢复科研工作台数据。

用法：
    python scripts/recover_workbench_browser_data.py
    python scripts/recover_workbench_browser_data.py --port 4387

不指定端口时仅从项目日志中列出候选端口。指定端口后，脚本会严格监听该
端口并打开恢复页；浏览器同源规则因此允许页面读取该端口过去留下的数据。
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.script.workbench_host import create_workbench_server, workbench_html_path

PORT_PATTERN = re.compile(r"http://127\.0\.0\.1:(\d+)")


def discover_candidate_ports() -> list[int]:
    ports: set[int] = set()
    log_root = PROJECT_ROOT / "logs"
    if not log_root.exists():
        return []
    for log_path in log_root.rglob("*.log"):
        try:
            content = log_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        ports.update(int(match) for match in PORT_PATTERN.findall(content))
    return sorted(port for port in ports if 1 <= port <= 65535)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="恢复旧随机端口下的爱弥斯科研工作台浏览器数据",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="需要恢复的历史端口；可先不带参数运行以查看日志候选",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = discover_candidate_ports()
    if args.port is None:
        if candidates:
            print("从项目日志发现的候选端口：")
            print("  " + ", ".join(str(port) for port in candidates))
            print("示例：python scripts/recover_workbench_browser_data.py --port 4387")
        else:
            print("项目日志中没有找到历史端口。请从旧日志或浏览器记录确认端口。")
        return 0
    if not 1 <= args.port <= 65535:
        print("端口必须在 1 到 65535 之间。", file=sys.stderr)
        return 2

    html = workbench_html_path()
    if not html.is_file():
        print(f"找不到工作台页面：{html}", file=sys.stderr)
        return 2
    try:
        server = create_workbench_server(
            html.parent,
            preferred_port=args.port,
            allow_fallback=False,
        )
    except OSError as exc:
        print(
            f"无法监听历史端口 {args.port}：{exc}\n"
            "请先关闭占用该端口的程序，再重新运行；脚本不会改用其他端口。",
            file=sys.stderr,
        )
        return 1

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = (
        f"http://127.0.0.1:{args.port}/{html.name}"
        "?recover_legacy=1"
    )
    print(f"恢复页已打开：{url}")
    print("请在浏览器查看恢复结果。完成后回到此窗口按 Enter 关闭临时服务。")
    webbrowser.open(url, new=2)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
