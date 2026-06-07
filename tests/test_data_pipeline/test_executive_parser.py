"""测试 executive_parser 模块"""
import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_compute_turnover_rate_basic():
    """正常计算 turnover"""
    from data_pipeline.executive_parser import compute_turnover_rate
    df = pd.DataFrame({
        0: ["姓名", "年龄", "职务", "起始日期", "终止日期"],
        1: ["张三", "45", "董事", "2020-01-01", "2023-12-31"],
        2: ["李四", "38", "监事", "2021-06-01", ""],
        3: ["王五", "42", "高管", "2022-03-15", "2024-01-01"],
    }).T
    rate = compute_turnover_rate(df, 2023)
    # 3 人中 1 人终止日期在 2023 年
    assert rate == pytest.approx(33.333333333333336)


def test_compute_turnover_rate_no_termination():
    """无终止日期列时返回 0.0"""
    from data_pipeline.executive_parser import compute_turnover_rate
    df = pd.DataFrame({
        0: ["姓名", "年龄", "职务"],
        1: ["张三", "45", "董事"],
        2: ["李四", "38", "监事"],
    }).T
    rate = compute_turnover_rate(df, 2023)
    assert rate == 0.0


def test_compute_turnover_rate_empty():
    """空 DataFrame 返回 0.0"""
    from data_pipeline.executive_parser import compute_turnover_rate
    rate = compute_turnover_rate(None, 2023)
    assert rate == 0.0


def test_compute_turnover_rate_none_terminated():
    """所有人都在职返回 0.0"""
    from data_pipeline.executive_parser import compute_turnover_rate
    df = pd.DataFrame({
        0: ["姓名", "职务", "起始日期", "终止日期"],
        1: ["张三", "董事", "2020-01-01", ""],
        2: ["李四", "监事", "2021-06-01", ""],
    }).T
    rate = compute_turnover_rate(df, 2023)
    assert rate == 0.0


def test_compute_turnover_rate_multiple_years():
    """多年度数据只统计指定年份"""
    from data_pipeline.executive_parser import compute_turnover_rate
    df = pd.DataFrame({
        0: ["姓名", "职务", "终止日期"],
        1: ["张三", "董事", "2022-12-31"],
        2: ["李四", "监事", "2023-06-30"],
        3: ["王五", "高管", "2024-01-01"],
    }).T
    rate = compute_turnover_rate(df, 2023)
    assert rate == pytest.approx(33.333333333333336)


def test_parse_executive_table_no_camelot():
    """Camelot 不可用时返回 None"""
    from data_pipeline.executive_parser import parse_executive_table, CAMELOT_AVAILABLE
    if not CAMELOT_AVAILABLE:
        result = parse_executive_table("nonexistent.pdf")
        assert result is None
