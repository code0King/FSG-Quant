"""
PDF 文本提取模块（主项目用）

提取路径: .md 缓存 → PyMuPDF 直接提取 → 写入缓存。
表格自动识别并渲染为 Markdown 表格格式。
pdfplumber 负责处理结构化表格数据（详见 executive_parser 模块）。

用法:
    from data_pipeline.pdf_extractor import extract_text
    text = extract_text("年报.pdf")
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import fitz
    FITZ_AVAILABLE = True
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="fitz")
except ImportError:
    FITZ_AVAILABLE = False
    logger.warning("PyMuPDF (fitz) not installed. Install: pip install PyMuPDF")

PDFPLUMBER_AVAILABLE = False
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    logger.warning("pdfplumber not installed. Install: pip install pdfplumber")

CACHE_DIR = Path("data/cache/parsed_pdf")

# 表格行数下限——小于此值不视为正经表格（过滤页眉页脚）
_MIN_TABLE_ROWS = 3
# 每页最大表格数（防止大量假阳性打乱输出流）
_MAX_TABLES_PER_PAGE = 50


def extract_text(pdf_path: str | Path, use_cache: bool = True) -> str:
    """
    提取 PDF 纯文本（含 Markdown 表格）。

    链路: .md 缓存 → PyMuPDF(含表格) → 空字符串

    Args:
        pdf_path: PDF 文件路径
        use_cache: 是否使用缓存（默认 True）

    Returns:
        提取的纯文本（表格部分渲染为 Markdown 表格）
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if use_cache:
        cached = _load_cache(pdf_path)
        if cached is not None:
            logger.debug(f"Loaded cached text for {pdf_path.name}")
            return cached

    text = ""
    if FITZ_AVAILABLE:
        text = _extract_with_pymupdf(pdf_path)

    if not text:
        logger.warning(f"No text extracted from {pdf_path.name}")
    elif use_cache:
        _save_cache(pdf_path, text, "pymupdf")

    return text


# ── PyMuPDF 提取（文本 + 表格检测） ──────────────────────


def _extract_with_pymupdf(pdf_path: Path) -> str:
    """
    使用 PyMuPDF 提取文本，自动检测表格并渲染为 Markdown 格式。
    按阅读顺序（垂直位置）混合输出文本段落和 Markdown 表格。
    """
    import fitz
    doc = fitz.open(str(pdf_path))
    pages_text = []
    for page_no, page in enumerate(doc, 1):
        content = _extract_page_mixed(page, page_no, doc.page_count)
        pages_text.append(content)
    doc.close()
    return "\n\n".join(pages_text)


def _extract_page_mixed(page, page_no: int, total: int) -> str:
    """提取单页内容：文本段落 + Markdown 表格，按阅读位置排序输出。"""
    blocks = page.get_text("dict")["blocks"]
    tables = page.find_tables()

    # 收集表格区域（bbox），用于后续去重
    table_regions = []
    table_md_list = []
    for t in tables.tables:
        data = t.extract()
        if not data or len(data) < _MIN_TABLE_ROWS:
            continue
        md = _table_to_markdown(data)
        if md:
            table_regions.append(t.bbox)
            table_md_list.append((t.bbox[1], md))  # (y_top, markdown)

    if not table_md_list:
        # 无有效表格，走传统纯文本
        lines = [span.get("text", "") for b in blocks
                 for line in b.get("lines", [])
                 for span in line.get("spans", [])]
        return "\n".join(lines)

    # 有表格：混合排列文本行和表格
    # 先收集所有文本行（含位置）
    text_lines = []  # [(y_top, text)]
    for b in blocks:
        bbox = b.get("bbox")
        if not bbox:
            continue
        # 跳过完全落入表格区域的文本块
        if _overlaps_table(bbox, table_regions):
            continue
        for line in b.get("lines", []):
            lbox = line.get("bbox")
            text = "".join(s.get("text", "") for s in line.get("spans", []))
            if text.strip():
                text_lines.append((lbox[1] if lbox else bbox[1], text))

    # 合并并排序（按垂直位置 y）
    all_items = text_lines + table_md_list
    all_items.sort(key=lambda x: x[0])

    # 剔除相邻重复的文本行
    result = []
    prev = None
    for _, content in all_items:
        if content != prev:
            result.append(content)
            prev = content
    return "\n".join(result)


def _overlaps_table(bbox, table_regions) -> bool:
    """判断 bbox 是否与任意表格区域重叠"""
    x0, y0, x1, y1 = bbox
    for tx0, ty0, tx1, ty1 in table_regions:
        if x0 < tx1 and x1 > tx0 and y0 < ty1 and y1 > ty0:
            return True
    return False


def _table_to_markdown(data: list[list]) -> str:
    """将表格提取数据（list of list）渲染为 Markdown 表格字符串"""
    if not data or len(data) < _MIN_TABLE_ROWS:
        return ""

    header = data[0]
    body = data[1:] if len(data) > 1 else []

    # 跳过全空行
    body = [row for row in body if any(cell and str(cell).strip() for cell in row)]

    if not body:
        return ""

    # 规范化列数
    ncols = len(header) if header else 1

    def _clean_cell(v):
        if v is None:
            return ""
        s = str(v).replace("\n", " ").strip()
        return s

    lines = []
    # 表头
    hdr = "| " + " | ".join(_clean_cell(header[i]) if i < len(header) else "" for i in range(ncols)) + " |"
    lines.append(hdr)
    # 分隔行
    sep = "| " + " | ".join("---" for _ in range(ncols)) + " |"
    lines.append(sep)
    # 数据行
    for row in body:
        vals = [_clean_cell(row[i]) if i < len(row) else "" for i in range(ncols)]
        lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines)


# ── Markdown 缓存（带 YAML 前言） ──────────────────────────

def _cache_path(pdf_path: Path) -> Path:
    """生成缓存文件路径（.md 后缀）"""
    return CACHE_DIR / f"{pdf_path.parent.name}_{pdf_path.stem}.md"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML 前言，返回 (metadata, body)"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


def _build_frontmatter(pdf_path: Path, extractor: str, chars: int) -> str:
    """构建 YAML 前言字符串"""
    return (
        "---\n"
        f"stock_code: {pdf_path.parent.name}\n"
        f"report_year: {pdf_path.stem}\n"
        f"extractor: {extractor}\n"
        f"chars: {chars}\n"
        f"cached_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "---\n"
    )


def _load_cache(pdf_path: Path) -> Optional[str]:
    """从 Markdown 缓存加载已提取文本（正文部分）"""
    md_file = _cache_path(pdf_path)
    if md_file.exists():
        raw = md_file.read_text(encoding="utf-8")
        _, body = _parse_frontmatter(raw)
        return body.strip()

    # 向后兼容：尝试旧的 .txt 缓存
    txt_file = CACHE_DIR / f"{pdf_path.parent.name}_{pdf_path.stem}.txt"
    if txt_file.exists():
        logger.info(f"Migrating legacy .txt cache to .md: {txt_file.name}")
        text = txt_file.read_text(encoding="utf-8")
        _save_cache(pdf_path, text, "unknown")
        txt_file.unlink(missing_ok=True)
        return text

    return None


def _save_cache(pdf_path: Path, text: str, extractor: str = "pymupdf"):
    """保存提取文本到 Markdown 缓存（带 YAML 前言）"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    md_file = _cache_path(pdf_path)
    frontmatter = _build_frontmatter(pdf_path, extractor, len(text))
    md_file.write_text(frontmatter + text + "\n", encoding="utf-8")
