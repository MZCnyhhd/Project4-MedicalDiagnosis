#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模块名称: build_site.py (静态站点组装脚本)

功能描述:
    将仓库中分散的知识库源文件组装进 `docs/kb/`，使 `docs/` 成为可直接发布的
    自包含静态站点（GitHub Pages 的发布源）。

    组装内容:
        _sidebar.md                  -> docs/kb/_sidebar.md
        home.md                      -> docs/kb/home.md
        data/knowledge_base/*.md     -> docs/kb/data/knowledge_base/*.md

    其中 `docs/kb/index.html` 与 `docs/kb/assets/`（docsify 运行时）为仓库内静态文件，
    不参与组装。

设计原则:
    1.  **单一数据源**: 侧边栏与首页始终以仓库根目录版本为准（由 tools/gen_sidebar.py 生成），
        避免在 docs/ 下维护重复副本。
    2.  **本地/CI 一致**: 本地预览与 GitHub Actions 调用同一脚本，杜绝两处逻辑分叉。
    3.  **幂等**: 可反复执行；默认先清理上次生成的产物再复制。

用法:
    python tools/build_site.py

依赖关系:
    - 仅使用 Python 标准库，无需额外依赖。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# ---- 路径常量 ----
ROOT = Path(__file__).resolve().parent.parent
KB_SRC = ROOT / "data" / "knowledge_base"
SITE_KB = ROOT / "docs" / "kb"
KB_DEST = SITE_KB / "data" / "knowledge_base"

# 需要同步到站点的根目录文件
ROOT_FILES = ["_sidebar.md", "home.md"]
# 生成物（每次组装前清理，避免陈旧词条残留）
GENERATED = [KB_DEST, SITE_KB / "_sidebar.md", SITE_KB / "home.md"]


def clean() -> None:
    """删除上次组装产生的文件与目录。"""
    for path in GENERATED:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def assemble() -> int:
    """执行组装，返回同步的词条数量。"""
    KB_DEST.mkdir(parents=True, exist_ok=True)

    # 1) 根目录的侧边栏 / 首页
    for name in ROOT_FILES:
        src = ROOT / name
        if not src.exists():
            raise FileNotFoundError(f"缺少源文件: {src}")
        shutil.copy2(src, SITE_KB / name)

    # 2) 知识库词条
    if not KB_SRC.is_dir():
        raise FileNotFoundError(f"缺少知识库目录: {KB_SRC}")

    count = 0
    for item in sorted(KB_SRC.iterdir()):
        if item.is_file() and item.suffix == ".md":
            shutil.copy2(item, KB_DEST / item.name)
            count += 1

    return count


def main() -> int:
    if not (SITE_KB / "index.html").exists():
        print(f"[错误] 未找到站点入口: {SITE_KB / 'index.html'}", file=sys.stderr)
        return 1

    clean()
    count = assemble()

    print("[完成] 静态站点已组装 -> docs/kb/")
    print(f"       词条数量 : {count}")
    print(f"       侧边栏   : docs/kb/_sidebar.md")
    print(f"       首页     : docs/kb/home.md")
    print(f"       输出目录 : {SITE_KB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
