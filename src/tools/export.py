"""
模块名称: Export Tools (导出工具)
功能描述:

    提供将诊断/体检分析结果导出为文件的功能。
    支持生成 Markdown 文件流，以及融合自 Project3-HealthInsights 的 reportlab PDF 导出。

设计理念:

    1.  **流式处理**: 使用 `io.BytesIO` 在内存中生成文件流，避免产生临时文件。
    2.  **格式通用**: Markdown 通用性强；PDF 便于分享与打印。
    3.  **中文兼容**: PDF 使用 reportlab 内置 CID 字体 STSong-Light，无需外部字体文件。

线程安全性:

    - 无状态函数，线程安全。

依赖关系:

    - 标准库 `io`。
    - `reportlab`: PDF 生成（可选，缺失时 PDF 导出降级不可用）。
"""

import io

# reportlab 为可选依赖，缺失时不影响 Markdown 导出
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    _REPORTLAB_AVAILABLE = True
except ImportError:
    _REPORTLAB_AVAILABLE = False


def generate_markdown(content: str) -> io.BytesIO:
    """生成 Markdown 文件流"""
    buffer = io.BytesIO()
    buffer.write(content.encode('utf-8'))
    buffer.seek(0)
    return buffer


def _remove_disclaimer(markdown_text: str) -> str:
    """移除免责声明章节（从标题开始到结尾）。"""
    for marker in ("### ⚠️ 免责声明", "### 免责声明"):
        if marker in markdown_text:
            return markdown_text.split(marker)[0].rstrip() + "\n"
    return markdown_text


def _sanitize_for_pdf(text: str) -> str:
    """清洗文本，避免 PDF 中出现乱码：移除 emoji/特殊符号，替换上标数字与微符号。"""
    replacements = {
        "🧍": "", "🩸": "", "🚽": "", "🖥️": "", "❤️": "", "⚠️": "",
        "◆": "", "■": "", "●": "", "○": "", "•": "", "▪": "", "◦": "",
        "▶": "", "►": "", "▸": "", "▹": "", "◾": "", "◼": "", "★": "", "☆": "",
        "**": "",
        "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
        "µ": "u",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # 移除字体可能不支持的非 BMP 字符
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF)


def create_analysis_pdf(markdown_text: str) -> bytes:
    """
    将 AI 分析的 Markdown 文本转换为 PDF 字节流（融合自 Project3-HealthInsights）。
    生成的 PDF 不含免责声明章节，并对特殊字符做清洗以减少乱码。
    :param markdown_text: Markdown 文本
    :return: PDF 字节流；若 reportlab 不可用则抛出 RuntimeError
    """
    if not _REPORTLAB_AVAILABLE:
        raise RuntimeError("未安装 reportlab，无法生成 PDF。请执行 pip install reportlab。")

    cleaned_text = _sanitize_for_pdf(_remove_disclaimer(markdown_text))

    # 注册支持中文的内置 CID 字体，避免导出 PDF 时出现乱码
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    base = styles["Normal"]
    base.fontName = "STSong-Light"
    base.leading = 16

    heading = ParagraphStyle("Heading", parent=base, fontSize=16, leading=20,
                             spaceBefore=8, spaceAfter=4, bold=True)
    subheading = ParagraphStyle("Subheading", parent=base, fontSize=14, leading=18,
                                spaceBefore=6, spaceAfter=2)

    story = []
    for raw in cleaned_text.split("\n"):
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 8))
            continue
        # 一级标题（### ）
        if line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), heading))
            continue
        # 二级标题（#### ）
        if line.startswith("#### "):
            story.append(Paragraph(line[5:].strip(), subheading))
            continue
        # 列表项
        if line.startswith("- "):
            story.append(Paragraph("• " + line[2:].strip(), base))
            continue
        # 表格：忽略表头分隔行，保留数据行
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and not set(parts) <= {":---", "---"}:
                story.append(Paragraph("  ".join(parts), base))
            continue
        # 普通文本
        story.append(Paragraph(raw.replace("  ", "&nbsp;&nbsp;"), base))
        story.append(Spacer(1, 4))

    doc.build(story)
    pdf_value = buffer.getvalue()
    buffer.close()
    return pdf_value
