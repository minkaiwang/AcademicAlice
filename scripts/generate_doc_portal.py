#!/usr/bin/env python3
"""Generate HTML portal: merged readme block + contribution cards + doc/*.txt cards."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "doc"
CONTRIB_DIR = DOC_DIR / "贡献名单和主播的狗盆"
PORTAL_PATH = ROOT / "AA使用必读.html"


def _relative_href(path: Path) -> str:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    return rel.as_posix()


def _render_cards(paths: list[Path]) -> str:
    cards: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        safe = html.escape(text)
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        cards.append(
            f"""        <article class="card">
            <header>
                <div class="eyebrow">{mtime}</div>
                <h3>{html.escape(path.stem)}</h3>
                <a class="download" href="{_relative_href(path)}" download>下载原文件</a>
            </header>
            <pre>{safe}</pre>
        </article>"""
        )
    return "\n".join(cards)


def _generate_portal() -> str:
    doc_files = sorted(DOC_DIR.glob("*.txt"))
    dev_contrib_files = sorted(CONTRIB_DIR.glob("开发贡献*.txt"))

    doc_cards = _render_cards(doc_files)
    contrib_cards = _render_cards(dev_contrib_files)
    particles_spans = "\n".join(
        f'            <span style="--i:{idx};"></span>' for idx in range(1, 25)
    )
    particle_css = "\n".join(
        (
            ".particles span:nth-child({i}) {{"
            " background:{color};"
            " animation-duration:{duration}s;"
            " animation-delay:-{delay:.2f}s;"
            " }}"
        ).format(
            i=i,
            color=("#FFB6C1", "#ADD8E6", "#d1f2ff", "#f8cde1")[i % 4],
            duration=4 + (i % 5),
            delay=i * 0.35,
        )
        for i in range(1, 25)
    )

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hero_subtitle = "桌宠 × 科研工作台合并版 · 贡献记录 · 文档 · LTS1.0.5pre1"
    harmony_font = "resc/FRONTS/HarmonyOS_Sans_SC_Bold.ttf"
    lahairoi_font = "resc/FRONTS/WuWa%20Lahai-Roi%20Regular.ttf"

    template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>学术爱丽丝资料舱 · LTS1.0.5pre1</title>
    <style>
        @font-face {{
            font-family: 'HarmonyOS Sans';
            src: url('{harmony_font}') format('truetype');
            font-display: swap;
        }}
        @font-face {{
            font-family: 'Lahairoi';
            src: url('{lahairoi_font}') format('truetype');
            font-display: swap;
        }}
        :root {{
            --pink: #FFB6C1;
            --cyan: #ADD8E6;
            --deep-blue: #234C80;
            --bg-dark: #04070c;
            --card-bg: rgba(5, 9, 18, 0.85);
            --border: rgba(173, 216, 230, 0.6);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            font-family: 'HarmonyOS Sans', 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            background: radial-gradient(circle at 20% 20%, rgba(255,182,193,0.3), transparent 65%),
                        radial-gradient(circle at 80% 0%, rgba(173,216,230,0.35), transparent 55%),
                        var(--bg-dark);
            color: #f8fbff;
            overflow-x: hidden;
        }}
        main {{
            position: relative;
            padding: 4rem clamp(1rem, 5vw, 4rem) 5rem;
            z-index: 1;
        }}
        .hero {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .hero h1 {{
            font-size: clamp(2.6rem, 4vw, 3.6rem);
            margin: 0;
            letter-spacing: 0.1em;
            color: var(--pink);
            text-shadow: 0 0 18px rgba(255,182,193,0.7);
        }}
        .hero p {{
            margin: 0.8rem auto 0;
            font-size: 1.1rem;
            color: rgba(255, 218, 230, 0.95);
            max-width: 820px;
            line-height: 1.6;
        }}
        .usage-links a {{
            color: var(--pink);
            text-decoration: underline;
            text-underline-offset: 3px;
        }}
        .usage-links a:hover {{ color: var(--cyan); }}
        .upstream-quote {{
            margin: 1rem 0 0;
            padding: 1rem 1rem 1rem 1.1rem;
            border-left: 4px solid var(--pink);
            background: rgba(5, 9, 18, 0.55);
            color: rgba(248, 251, 255, 0.92);
            font-size: 0.95rem;
            line-height: 1.55;
        }}
        .upstream-cite {{
            margin: 0.5rem 0 0;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.65);
        }}
        .merged-h3 {{
            font-size: 1.25rem;
            color: var(--cyan);
            margin: 1.5rem 0 0.5rem;
            border-left: 4px solid var(--pink);
            padding-left: 0.65rem;
        }}
        section {{
            margin-bottom: 3rem;
        }}
        section > h2 {{
            font-size: 1.8rem;
            color: var(--cyan);
            margin-bottom: 1rem;
            border-left: 4px solid var(--pink);
            padding-left: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
        }}
        .cards {{
            display: grid;
            gap: 1.5rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.5rem;
            box-shadow: 0 15px 45px rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(6px);
            position: relative;
            overflow: hidden;
        }}
        .card::before {{
            content: '';
            position: absolute;
            inset: 8px;
            border: 1px solid rgba(255,182,193,0.15);
            border-radius: 12px;
            pointer-events: none;
        }}
        .card header {{
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 0.8rem;
            margin-bottom: 1rem;
        }}
        .card h3 {{
            margin: 0;
            font-size: 1.3rem;
            color: var(--pink);
        }}
        .card .eyebrow {{
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.2em;
            color: rgba(255,255,255,0.7);
        }}
        .card .download {{
            margin-left: auto;
            text-decoration: none;
            color: var(--cyan);
            font-size: 0.9rem;
            border-bottom: 1px solid transparent;
            transition: border 0.2s;
        }}
        .card .download:hover {{ border-color: var(--cyan); }}
        pre {{
            margin: 0;
            font-size: 0.9rem;
            line-height: 1.5;
            white-space: pre-wrap;
            color: #e7ebff;
        }}
        figure {{
            margin: 1rem auto 0;
            max-width: 360px;
            text-align: center;
        }}
        figure img {{
            width: 100%;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.25);
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
        }}
        figure figcaption {{
            margin-top: 0.6rem;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.8);
        }}
        footer {{
            text-align: center;
            padding: 2rem 1rem 4rem;
            font-size: 0.85rem;
            color: rgba(255,255,255,0.65);
        }}
        .section-desc {{
            color: rgba(255,255,255,0.85);
            max-width: 720px;
            margin-bottom: 1rem;
            line-height: 1.5;
        }}
        .trail-container {{
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 3;
        }}
        .trail-letter {{
            position: absolute;
            font-family: 'Lahairoi', 'HarmonyOS Sans', sans-serif;
            font-weight: 600;
            font-size: 1.2rem;
            color: var(--pink);
            opacity: 0.9;
            animation: trailBurst 0.9s ease-out forwards;
            text-shadow: 0 0 12px rgba(255,182,193,0.8), 0 0 24px rgba(173,216,230,0.6);
        }}
        @keyframes trailBurst {{
            0% {{ transform: translate3d(0,0,0) scale(1); opacity: 0.95; }}
            100% {{ transform: translate3d(var(--dx, 0px), var(--dy, -60px), 0) scale(0.3); opacity: 0; }}
        }}
        .particles {{
            position: fixed;
            inset: 0;
            overflow: hidden;
            pointer-events: none;
            z-index: 0;
        }}
        .particles span {{
            position: absolute;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            opacity: 0.8;
            animation: float 8s linear infinite;
            left: calc(4% * var(--i));
            top: calc(3% * var(--i));
            box-shadow: 0 0 12px currentColor;
        }}
{particle_css}
        @keyframes float {{
            0% {{ transform: translate3d(0, 0, 0); opacity: 0; }}
            20% {{ opacity: 0.85; }}
            100% {{ transform: translate3d(40px, -120px, 0); opacity: 0; }}
        }}
        @media (min-width: 768px) {{
            .cards {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
        }}
    </style>
</head>
<body>
    <div class="particles">
{particles}
    </div>
    <div class="trail-container" id="trail-root"></div>
    <main>
        <div class="hero">
            <h1>学术爱丽丝资料舱</h1>
            <p>{hero_subtitle}<br>本页由脚本根据仓库内文本自动生成，仅供查阅；权利义务与素材范围以各源文件及根目录 LICENSE 类文件为准。粉青配色与粒子动效为门户样式。生成时间：{timestamp}</p>
        </div>
        <section id="merged-readme">
            <h2>合并版 · 使用必读</h2>
            <p class="section-desc">
                本应用在<strong>同一 Windows 进程</strong>中整合了两类组件：（1）<strong>桌宠与 AI 交互</strong>，代码与资源与「飞行雪绒 / FlyingSnowVelvet-Aemeath」系项目同源或可溯源，非代码素材的权属与限制见 <code>LICENSE-ASSETS</code>；
                （2）<strong>科研工作台</strong>为内嵌静态页（<code>resc/workbench/</code>），在信息架构与交互上参考了
                <a href="https://github.com/AugustUp/phd_master_system" target="_blank" rel="noopener">AugustUp/phd_master_system</a>（MIT），本仓已做 Tailwind 本地化、主题与宿主衔接等改造，<strong>不等同于</strong>对该上游仓库的完整镜像。
                论文、项目、任务等数据以浏览器内 <strong>科研工作台</strong> 为主（多存于本机页面存储）；应用侧学术库路径见 <code>PROGRESS.md</code>、<code>resc/workbench/README.txt</code>。
            </p>
            <h3 class="merged-h3">博士工作台 · 上游仓库</h3>
            <p class="section-desc" style="margin-top:0.35rem;">
                原仓库：<a href="https://github.com/AugustUp/phd_master_system" target="_blank" rel="noopener noreferrer">AugustUp/phd_master_system</a>（MIT）。
                下列文字为该仓库 readme 的<strong>摘录</strong>，著作权与立场归原维护者；若与 GitHub 最新 readme 不一致，以原仓库为准。
            </p>
            <blockquote class="upstream-quote">
                感谢小红书用户分享的源文件，我在原有基础上完善了桌面端与移动端适配，并新增了坚果云网盘数据同步功能。 衷心鸣谢直接提供源码参考的用户： 「不是黑子是癫子」— 小红书号：61709040774 「橘子汽水」— 小红书号：romantic_Ksir 同时也向为上述源码提供者贡献内容的原始作者们致以谢意。本项目仅用于学习交流，非商业用途、未用于盈利。如涉及侵权，请通过 Issue 联系，我将立即处理删库。
            </blockquote>
            <p class="upstream-cite">摘录目的：向博士工作台来源链路的贡献者致谢；本分支内嵌页为改编实现，非上游应用完整镜像。</p>
            <h3 class="merged-h3">本分支维护者（合并与文档署名）</h3>
            <p class="section-desc" style="margin-top:0.35rem;">
                哔哩哔哩「靓点迷人」（标识 <code>bili_2719061712</code>，空间 <a href="https://space.bilibili.com/2719061712" target="_blank" rel="noopener noreferrer">space.bilibili.com/2719061712</a>）；
                小红书「皮鼓很痒」（小红书号 <code>533497202</code>）。
                应用内托盘「关注作者」链接以 <code>app_brand.py</code> 中 <code>AUTHOR_BILIBILI_SPACE_URL</code> 为准，可与本段文档署名分别配置。
            </p>
            <ul class="section-desc usage-links" style="margin-top:0;padding-left:1.25rem;">
                <li><strong>相对「分别使用桌宠与工作台」的主要差异（概要）</strong>：统一产品与人设「学术爱丽丝」、<code>resc/persona.txt</code> 系统提示、专用聊天窗口（粉系 UI，与桌旁气泡共用聊天管线）、命令面板 / 托盘与学术模块的联动、工作台多主题与离线 bundle 说明见 <code>resc/workbench/README.txt</code>。</li>
                <li><strong>工程文档</strong>：<a href="PRODUCT.md">PRODUCT.md</a>（品牌与中文口径）、<a href="PROGRESS.md">PROGRESS.md</a>（里程碑与技术约定）、<a href="README.md">README.md</a>（仓库总览）。</li>
                <li><strong>操作入口摘要</strong>：见下方 DOC 区「合并项目与使用入口」卡片原文。</li>
            </ul>
        </section>
        <section id="contrib">
            <h2>贡献列表</h2>
            <p class="section-desc">以下内容来自 <code>doc/贡献名单和主播的狗盆/</code> 下匹配 <code>开发贡献*.txt</code> 的文件原文，仅作署名与致谢记录；与当前维护者商业行为无关。</p>
            <div class="cards">
{contrib_cards}
            </div>
        </section>
        <section id="documents">
            <h2>DOC</h2>
            <div class="cards">
{doc_cards}
            </div>
        </section>
    </main>
    <footer>由 <code>scripts/generate_doc_portal.py</code> 根据仓库内文本生成 · LTS1.0.5pre1 · 不含赞助或打赏展示区块</footer>
    <script>
    (() => {{
        const letters = "FLYINGSNOWVELVET";
        const trailRoot = document.getElementById("trail-root");
        if (!trailRoot) return;
        document.addEventListener("mousemove", (event) => {{
            const span = document.createElement("span");
            span.className = "trail-letter";
            span.textContent = letters[Math.floor(Math.random() * letters.length)];
            span.style.left = `${{event.clientX}}px`;
            span.style.top = `${{event.clientY}}px`;
            const dx = (Math.random() * 80) - 40;
            const dy = -30 - Math.random() * 80;
            span.style.setProperty("--dx", `${{dx}}px`);
            span.style.setProperty("--dy", `${{dy}}px`);
            trailRoot.appendChild(span);
            setTimeout(() => span.remove(), 900);
        }});
    }})();
    </script>
</body>
</html>
"""

    return template.format(
        particle_css=particle_css,
        particles=particles_spans,
        hero_subtitle=hero_subtitle,
        timestamp=timestamp,
        doc_cards=doc_cards,
        contrib_cards=contrib_cards,
        harmony_font=harmony_font,
        lahairoi_font=lahairoi_font,
    )


def main() -> None:
    html_text = _generate_portal()
    PORTAL_PATH.write_text(html_text, encoding="utf-8")
    print(f"Wrote {PORTAL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
