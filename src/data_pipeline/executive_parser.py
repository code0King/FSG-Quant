"""
董监高表格解析模块

使用 Camelot 提取年报中"董事、监事、高级管理人员和员工情况"章节的任职表格，
计算核心人员变动率。

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

CAMELOT_AVAILABLE = False


def _init_deps():
    global CAMELOT_AVAILABLE
    try:
        import camelot
        CAMELOT_AVAILABLE = True
    except ImportError:
        logger.warning("camelot-py not installed. Install: pip install camelot-py")


_init_deps()


def parse_executive_table(pdf_path: str | Path) -> Optional[pd.DataFrame]:
    """
    从年报 PDF 中提取董监高任职表格。

    降级: Camelot 不可用时返回 None。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        DataFrame 包含任职信息，或 None
    """
    if not CAMELOT_AVAILABLE:
        logger.warning("Camelot not available, skipping executive table parsing")
        return None

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import camelot
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        if tables.n == 0:
            logger.debug(f"No lattice tables found in {pdf_path.name}, trying stream flavor")
            tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="stream")

        if tables.n == 0:
            logger.info(f"No tables found in {pdf_path.name}")
            return None

        # 合并所有表格
        combined = pd.concat([t.df for t in tables], ignore_index=True)
        # 过滤掉表头行（合并后第一行可能是重复表头）
        combined = combined.dropna(how="all").reset_index(drop=True)
        logger.info(f"Extracted {len(combined)} rows from {pdf_path.name}")
        return combined

    except Exception as e:
        logger.error(f"Camelot table extraction failed for {pdf_path.name}: {e}")
        return None


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
        # 跳过表头行
        is_header = any(kw in val for kw in _TERMINATION_KEYWORDS)
        if is_header:
            continue
        if not val or val in ("-", "—", "", "nan"):
            total += 1
            continue
        # 提取四位年份
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
        # 检查表头行（第一行）
        header = str(df.iloc[0, col_idx])
        for kw in keywords:
            if kw in header:
                return col_idx
    # 第二遍：检查所有行
    for col_idx in range(df.shape[1]):
        for row_idx in range(min(3, df.shape[0])):
            val = str(df.iloc[row_idx, col_idx])
            for kw in keywords:
                if kw in val:
                    return col_idx
    return None
