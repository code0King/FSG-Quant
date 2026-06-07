"""
行情数据桥接：quant_DB → FSG-Quant 格式

使用 quant_DB 统一外部数据接口 get_daily_bars 获取日线行情，
转换为 FSG-Quant 期望的格式：
  symbol (600000.SH) → stock_code (600000.SH)
  保留 close (收盘价) 和 adj_close (后复权收盘价)

用法:
    python scripts/market_bridge.py --years 2023
    python scripts/market_bridge.py --years 2021 2022 2023
"""
import argparse
import sys
from pathlib import Path
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ── quant_DB 统一外部接口 ──────────────────────────────────
QUANTDB_PROJECT = Path(r"D:\vscode-project\quant_DB")
sys.path.insert(0, str(QUANTDB_PROJECT))

from data.database import QuantDatabase
from data.engine import get_daily_bars

QUANTDB_BASE = Path(r"D:\vscode-project\quant_DB\data")
OUTPUT_DIR = Path("data/market_data/daily_quotes")


def convert_market_data(year, output_dir):
    logger.info(f"Fetching daily bars for {year} via quant_DB engine ...")

    qdb = QuantDatabase(base_path=str(QUANTDB_BASE))

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    try:
        result = get_daily_bars(
            symbols=[],  # 空列表表示全部股票
            fields="symbol,trade_date,close,volume,close_badj",
            start_date=start_date,
            end_date=end_date,
            df=True,
            db=qdb,
        )
    except Exception as e:
        logger.error(f"get_daily_bars failed for {year}: {e}")
        return

    if result is None or result.empty:
        logger.warning(f"No data returned for {year}")
        return

    # get_daily_bars 返回 symbol 已是 ts_code 格式 (600000.SH)
    result = result.rename(columns={
        'symbol': 'stock_code',
        'close_badj': 'adj_close',
    })
    result = result.sort_values(['stock_code', 'trade_date']).reset_index(drop=True)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'{year}.parquet'
    result.to_parquet(output_path, index=False)

    logger.info(f"Written: {output_path} ({len(result)} rows, {result['stock_code'].nunique()} stocks)")


def main():
    parser = argparse.ArgumentParser(description='行情数据桥接 (quant_DB engine)')
    parser.add_argument('--years', nargs='+', type=int, required=True,
                        help='需要转换的年份，如 2023')
    parser.add_argument('--output-dir', default=str(OUTPUT_DIR),
                        help=f'输出目录 (default: {OUTPUT_DIR})')
    parser.add_argument('--quantdb-path', default=str(QUANTDB_BASE),
                        help=f'quant_DB 数据根路径')
    args = parser.parse_args()

    global QUANTDB_BASE
    QUANTDB_BASE = Path(args.quantdb_path)

    for year in sorted(set(args.years)):
        convert_market_data(year, args.output_dir)

    print(f"\n行情数据转换完成！文件保存在: {args.output_dir}")


if __name__ == '__main__':
    main()
