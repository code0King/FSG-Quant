"""
全流程运行：pdfplumber 提取核心人员表格 → MD 缓存 → 变动率计算

用法:
    python scripts/run_executive_pipeline.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from data_pipeline.executive_parser import (
    parse_executive_table, compute_turnover_rate, save_executive_table_to_md
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PDF_BASE = Path("data/raw/annual_reports")
STOCKS = ["000001.SZ", "000002.SZ", "000858.SZ", "300750.SZ", "600519.SH"]
YEARS = [2021, 2022, 2023, 2024, 2025]

results = []
for code in STOCKS:
    for year in YEARS:
        pdf_path = PDF_BASE / code / f"{year}.pdf"
        if not pdf_path.exists():
            logger.warning(f"Missing PDF: {pdf_path}")
            continue

        df = parse_executive_table(pdf_path)

        # 保存原始表格到 MD
        md_path = save_executive_table_to_md(df, code, year, pdf_path)

        # 计算变动率
        rate = compute_turnover_rate(df, year)

        row_count = len(df) if df is not None else 0
        md_status = "✓" if md_path else "—"
        results.append((code, year, row_count, rate, md_status))
        logger.info(f"{code} {year}: {row_count} rows, turnover={rate:.1f}%, MD={md_status}")

print("\n" + "=" * 80)
print(f"{'股票':<12} {'年份':<6} {'表格行数':<10} {'变动率%':<10} {'MD缓存':<8}")
print("=" * 80)
for code, year, rows, rate, md in results:
    print(f"{code:<12} {year:<6} {rows:<10} {rate:<10.1f} {md:<8}")
print("=" * 80)

# 检查缓存目录
cache_dir = Path("data/cache/executive_tables")
if cache_dir.exists():
    md_files = list(cache_dir.glob("*.md"))
    print(f"\n核心人员表格 MD 文件: {len(md_files)} 个 → {cache_dir}/")
    for f in sorted(md_files):
        print(f"  {f.name}")
