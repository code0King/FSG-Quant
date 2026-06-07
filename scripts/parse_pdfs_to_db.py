"""
批量解析年报PDF并将结构化数据写入SQLite

用法:
    python scripts/parse_pdfs_to_db.py --all
    python scripts/parse_pdfs_to_db.py --stocks 000001.SZ 600519.SH --years 2023
"""
import argparse
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from data_pipeline.pdf_parser import AnnualReportParser, save_mda_to_db, save_governance_from_pdf

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
_log_file = LOG_DIR / f"parse_pdfs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Log file: {_log_file}")

PDF_DIR = Path("data/raw/annual_reports")
DB_PATH = Path("data/raw/financial_data.sqlite")


def ensure_tables():
    """确保数据库表存在"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS governance_data (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            audit_opinion TEXT,
            is_standard_audit INTEGER,
            major_shareholder_pledge_ratio REAL,
            core_personnel_turnover_rate REAL DEFAULT 0.0,
            PRIMARY KEY (stock_code, report_year)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mda_text (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            mda_text TEXT,
            PRIMARY KEY (stock_code, report_year)
        )
    """)
    conn.commit()
    conn.close()


def get_stock_years_from_db():
    """从SQLite获取已有的股票和年份列表"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT stock_code FROM financial_annual")
    stocks = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT report_year FROM financial_annual")
    years = sorted([r[0] for r in cursor.fetchall()])
    conn.close()
    return stocks, years


def get_stock_years_from_pdfs(pdf_dir: Path):
    """从PDF文件结构获取股票和年份"""
    stocks = []
    for d in pdf_dir.iterdir():
        if d.is_dir():
            for f in d.glob("*.pdf"):
                year = int(f.stem)
                stocks.append((d.name, year))
    return stocks


def parse_single(parser: AnnualReportParser, stock_code: str, year: int, db_path: str) -> bool:
    """解析单个PDF并写入数据库"""
    pdf_path = PDF_DIR / stock_code / f"{year}.pdf"

    if not pdf_path.exists():
        logger.warning(f"PDF not found: {pdf_path}")
        return False

    try:
        result = parser.parse(str(pdf_path))

        # 保存MD&A
        if result.get('mda_text'):
            save_mda_to_db(db_path, stock_code, year, result['mda_text'])

        # 保存治理数据
        save_governance_from_pdf(
            db_path, stock_code, year,
            audit_opinion=result.get('audit_opinion'),
            is_standard=result.get('is_standard_audit'),
            pledge_ratio=result.get('pledge_ratio'),
        )
        return True
    except Exception as e:
        logger.error(f"Failed to parse {stock_code} {year}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='批量解析年报PDF写入数据库')
    parser.add_argument('--stocks', nargs='+', default=None, help='股票代码 如 000001.SZ')
    parser.add_argument('--years', nargs='+', type=int, default=None, help='年份')
    parser.add_argument('--all', action='store_true', help='解析所有已有PDF')

    args = parser.parse_args()
    pdf_dir = PDF_DIR

    if args.all:
        entries = get_stock_years_from_pdfs(pdf_dir)
        stock_years = {}
        for stock, year in entries:
            stock_years.setdefault(stock, []).append(year)
    elif args.stocks:
        years = args.years or [2023]
        stock_years = {s: years for s in args.stocks}
    else:
        print("请指定 --stocks 或 --all")
        return

    ensure_tables()
    pdf_parser = AnnualReportParser()

    results = {'success': 0, 'failed': 0}
    for stock, years in stock_years.items():
        for year in years:
            logger.info(f"--- {stock} {year} ---")
            if parse_single(pdf_parser, stock, year, str(DB_PATH)):
                results['success'] += 1
            else:
                results['failed'] += 1

    logger.info(f"Done: {results['success']} success, {results['failed']} failed")


if __name__ == '__main__':
    main()
