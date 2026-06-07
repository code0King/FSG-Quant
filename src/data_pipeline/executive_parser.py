"""
董监高表格解析模块

使用 pdfplumber 提取年报中"董事、监事、高级管理人员和员工情况"章节的任职表格，
计算核心人员变动率，并将原始表格数据以 MD 格式保存到 data/cache。

用法:
    from data_pipeline.executive_parser import parse_executive_table, compute_turnover_rate
    df = parse_executive_table("年报.pdf")
    rate = compute_turnover_rate(df, 2023)
"""
import re
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

PDFPLUMBER_AVAILABLE = False


def _init_deps():
    global PDFPLUMBER_AVAILABLE
    try:
        import pdfplumber
        PDFPLUMBER_AVAILABLE = True
    except ImportError:
        logger.warning("pdfplumber not installed. Install: pip install pdfplumber")


_init_deps()

# 核心人员表格关键词（用于筛选包含董监高信息的表格）
_EXECUTIVE_KEYWORDS = [
    "姓名", "职务", "董事", "监事", "高级管理人员",
    "任职", "起始日期", "终止日期", "离职", "任期",
    "董事会", "监事会", "高管",
]
# 跳过明显不是董监高表格的关键词（如财务报表类）
_SKIP_KEYWORDS = [
    "利润表", "资产负债表", "现金流量表", "所有者权益变动表",
    "合并资产负债表", "合并利润表",
]

# 原始表格缓存目录
RAW_TABLE_CACHE_DIR = Path("data/cache/executive_tables")


def parse_executive_table(pdf_path: str | Path) -> Optional[pd.DataFrame]:
    """
    从年报 PDF 中使用 pdfplumber 提取董监高任职表格。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        DataFrame 包含任职信息，或 None
    """
    if not PDFPLUMBER_AVAILABLE:
        logger.warning("pdfplumber not available, skipping executive table parsing")
        return None

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import pdfplumber
        all_rows = []
        seen = set()

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 3:
                        continue

                    # 检查是否为董监高表格
                    header_text = " ".join(str(cell or "") for cell in table[0])
                    if not _is_executive_table(header_text):
                        continue

                    # 提取数据行
                    for row in table[1:]:
                        row_key = tuple(str(c or "") for c in row)
                        if row_key in seen:
                            continue
                        seen.add(row_key)
                        all_rows.append(row)

                    logger.debug(
                        f"Found executive table on page {page_num} "
                        f"({len(table)} rows)")

        if not all_rows:
            logger.info(f"No executive tables found in {pdf_path.name}")
            return None

        df = pd.DataFrame(all_rows)
        # 如果第一行看起来像表头（包含姓名、职务等关键词），将其作为列名
        first_row = [str(c or "") for c in df.iloc[0]]
        if any(kw in "".join(first_row) for kw in ["姓名", "职务", "董事"]):
            df.columns = first_row
            df = df.iloc[1:].reset_index(drop=True)

        df = df.dropna(how="all").reset_index(drop=True)
        logger.info(f"Extracted {len(df)} rows from {pdf_path.name}")
        return df

    except Exception as e:
        logger.error(f"pdfplumber table extraction failed for {pdf_path.name}: {e}")
        return None


def _is_executive_table(header_text: str) -> bool:
    """判断表格标题行是否属于董监高任职表格"""
    header_lower = header_text.lower()
    for kw in _SKIP_KEYWORDS:
        if kw in header_text:
            return False
    match_count = sum(1 for kw in _EXECUTIVE_KEYWORDS if kw in header_text)
    return match_count >= 2


def save_executive_table_to_md(df: Optional[pd.DataFrame],
                                stock_code: str, year: int,
                                pdf_path: Optional[str | Path] = None) -> Optional[Path]:
    """
    将核心人员任职表格原始数据保存为 MD 文档到 data/cache 目录。

    文件名格式: {stock_code}_{year}_executive.md
    文件头包含 YAML 前言描述元数据。

    Args:
        df: 任职表格 DataFrame
        stock_code: 股票代码
        year: 报告年份
        pdf_path: 原始 PDF 路径（可选，用于元数据）

    Returns:
        保存的 MD 文件路径，或 None
    """
    if df is None or df.empty:
        logger.warning(f"No executive table data to save for {stock_code} {year}")
        return None

    cache_dir = RAW_TABLE_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    md_path = cache_dir / f"{stock_code}_{year}_executive.md"

    source = str(pdf_path) if pdf_path else f"{stock_code}/{year}.pdf"
    rows = len(df)
    cols = len(df.columns)

    lines = ["---"]
    lines.append(f"stock_code: {stock_code}")
    lines.append(f"report_year: {year}")
    lines.append(f"source: {source}")
    lines.append(f"rows: {rows}")
    lines.append(f"columns: {cols}")
    lines.append(f"extractor: pdfplumber")
    lines.append("---")
    lines.append("")
    lines.append(f"# 核心人员任职信息 — {stock_code} {year}")
    lines.append("")
    lines.append(f"> 原始表格数据，共 {rows} 行，{cols} 列")
    lines.append("")

    # 用 DataFrame 的列作为表头
    col_names = list(df.columns) if hasattr(df, 'columns') else [f"col_{i}" for i in range(cols)]
    header = "| " + " | ".join(str(c) for c in col_names) + " |"
    sep = "| " + " | ".join("---" for _ in range(cols)) + " |"
    lines.append(header)
    lines.append(sep)

    for _, row in df.iterrows():
        vals = [str(v).replace("\n", " ") if v is not None else "" for v in row]
        lines.append("| " + " | ".join(vals) + " |")

    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Saved executive table MD: {md_path}")
    return md_path


# 关键词常量
_TERMINATION_KEYWORDS = ["终止日期", "离职日期", "离任日期", "离职时间"]


def compute_turnover_rate(df: Optional[pd.DataFrame], year: int) -> float:
    """
    从任职表格计算核心人员变动率。

    策略: 查找含有"终止日期"或离职信息的列，统计终止日期在本年的人数占比。

    Args:
        df: 任职表格 DataFrame
        year: 报告年份

    Returns:
        变动率（百分比 0-100）
    """
    if df is None or df.empty:
        return 0.0

    date_col_idx = _find_column(df, _TERMINATION_KEYWORDS)
    if date_col_idx is None:
        logger.debug("No termination date column found, turnover = 0.0")
        return 0.0

    terminated = 0
    total = 0
    for _, row in df.iterrows():
        val = str(row.iloc[date_col_idx]).strip()
        is_header = any(kw in val for kw in _TERMINATION_KEYWORDS)
        if is_header:
            continue
        if not val or val in ("-", "—", "", "nan"):
            total += 1
            continue
        m = re.search(r"(\d{4})", val)
        if m:
            end_year = int(m.group(1))
            total += 1
            if end_year == year:
                terminated += 1
        else:
            total += 1

    if total == 0:
        return 0.0

    rate = terminated / total * 100
    logger.info(f"Executive turnover: {terminated}/{total} = {rate:.1f}%")
    return min(100.0, max(0.0, rate))


def _find_column(df: pd.DataFrame, keywords: list[str]) -> Optional[int]:
    """在 DataFrame 中查找包含任一关键词的列索引"""
    for col_idx in range(df.shape[1]):
        header = str(df.iloc[0, col_idx])
        for kw in keywords:
            if kw in header:
                return col_idx
    for col_idx in range(df.shape[1]):
        for row_idx in range(min(3, df.shape[0])):
            val = str(df.iloc[row_idx, col_idx])
            for kw in keywords:
                if kw in val:
                    return col_idx
    return None
