"""
quant_DB → FSG-Quant SQLite 数据桥接

从 quant_DB（Parquet 格式）读取财务数据，构建 FSG-Quant 所需的 SQLite 数据库。

使用 quant_DB 统一外部数据接口 (data.engine):
  - QuantDatabase: 统一路径管理
  - get_finance_deriv: 财务衍生指标查询
  - get_daily_bars: 日线行情查询
  - get_daily_valuation: 每日估值查询

大股东质押比例通过 akshare.stock_gpzy_pledge_ratio_em 获取，
写入本地 Parquet 缓存（data/cache/pledge_ratio_cache.parquet），
网络不可用时自动从缓存读取。

用法:
    python scripts/quantdb_bridge.py --sample 5 --years 2021 2022 2023
    python scripts/quantdb_bridge.py --stocks 000001.SZ 600519.SH --years 2023
"""
import sqlite3
import argparse
import sys
from pathlib import Path
import logging
from datetime import datetime

import pandas as pd
import numpy as np
import akshare as ak

from data_pipeline.executive_parser import parse_executive_table, compute_turnover_rate

# ── quant_DB 路径 ────────────────────────────────────────
QUANTDB_PROJECT = Path(r"D:\vscode-project\quant_DB")
sys.path.insert(0, str(QUANTDB_PROJECT))

from data.database import QuantDatabase

logger = logging.getLogger(__name__)

# ── 路径配置 ───────────────────────────────────────────────
DEFAULT_QUANTDB_PATH = QUANTDB_PROJECT / "data"
DEFAULT_OUTPUT_DB = Path("data/raw/financial_data.sqlite")
PLEDGE_CACHE_PATH = Path("data/cache/pledge_ratio_cache.parquet")
TURNOVER_CACHE_PATH = Path("data/cache/executive_turnover_cache.parquet")


def _init_quantdb(base_path: str | Path) -> QuantDatabase:
    """初始化 QuantDatabase 实例（统一路径管理）"""
    return QuantDatabase(base_path=str(base_path))


def _load_financial_parquet(table_name: str, db: QuantDatabase) -> pd.DataFrame:
    """通过 QuantDatabase 路径管理加载财务 parquet 文件"""
    fp = db.financials_path / f'{table_name}.parquet'
    if not fp.exists():
        raise FileNotFoundError(f"quant_DB file not found: {fp}")
    df = pd.read_parquet(fp, engine='pyarrow')
    if 'report_type' in df.columns:
        df = df[df['report_type'] == 12].copy()
    return df


def _code_to_stock_code(code_raw: str) -> str | None:
    """6位数字代码转统一股票代码（带交易所后缀）"""
    prefix = code_raw[:3]
    if prefix in ('600', '601', '603', '605', '688', '689'):
        return f"{code_raw}.SH"
    if prefix in ('000', '001', '002', '003', '300', '301'):
        return f"{code_raw}.SZ"
    if prefix in ('830', '831', '832', '833', '834', '835', '836', '837',
                  '838', '839', '870', '871', '872', '873', '874', '875',
                  '876', '877', '878', '879', '880', '881', '882', '883',
                  '884', '885', '886', '887', '888', '889', '920', '921',
                  '922', '923'):
        return f"{code_raw}.BJ"
    return None


def _parse_pledge_df(df: pd.DataFrame) -> dict[str, float]:
    """解析 akshare 质押比例 DataFrame → {stock_code: ratio}"""
    cols = df.columns.tolist()
    code_col = next(c for c in cols if "股票代码" in c or "代码" in c)
    ratio_col = next(c for c in cols if "质押比例" in c)
    mapping: dict[str, float] = {}
    for _, row in df.iterrows():
        code_raw = str(row[code_col]).strip().zfill(6)
        ratio_val = pd.to_numeric(row[ratio_col], errors='coerce')
        if pd.isna(ratio_val):
            continue
        sc = _code_to_stock_code(code_raw)
        if sc is not None:
            mapping[sc] = float(ratio_val)
    return mapping


def _fetch_pledge_from_akshare(years: list[int]) -> dict[int, dict[str, float]]:
    """从 akshare 在线获取，返回 {year: {stock_code: ratio}}"""
    result: dict[int, dict[str, float]] = {}
    for y in years:
        found = None
        for d in [f"{y}1229", f"{y}1230", f"{y}1231", f"{y+1}0103", f"{y+1}0104", f"{y+1}0105"]:
            try:
                logger.info(f"  Fetching akshare pledge ratio for {y} with date={d}...")
                raw = ak.stock_gpzy_pledge_ratio_em(date=d)
                if raw is not None and not raw.empty:
                    found = (raw, d)
                    break
            except Exception:
                continue
        if found is None:
            logger.warning(f"No akshare pledge data available for year {y}")
            continue
        raw, used_date = found
        logger.info(f"  Got {len(raw)} records for {y} (date={used_date})")
        result[y] = _parse_pledge_df(raw)
    return result


def _load_pledge_from_cache() -> dict[int, dict[str, float]] | None:
    """从本地缓存加载"""
    if not PLEDGE_CACHE_PATH.exists():
        return None
    try:
        df = pd.read_parquet(PLEDGE_CACHE_PATH)
        result: dict[int, dict[str, float]] = {}
        for year, grp in df.groupby("report_year"):
            result[int(year)] = dict(zip(grp["stock_code"], grp["pledge_ratio"]))
        logger.info(f"  Loaded {len(df)} pledge records from cache ({PLEDGE_CACHE_PATH})")
        return result
    except Exception as e:
        logger.warning(f"Failed to load pledge cache: {e}")
        return None


def _save_pledge_to_cache(akshare_data: dict[int, dict[str, float]]):
    """将 akshare 数据写入本地缓存"""
    rows = []
    for year, mapping in akshare_data.items():
        for sc, ratio in mapping.items():
            rows.append({"stock_code": sc, "report_year": year, "pledge_ratio": ratio})
    if not rows:
        return
    df = pd.DataFrame(rows)
    PLEDGE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PLEDGE_CACHE_PATH, index=False)
    logger.info(f"  Saved {len(df)} pledge records to cache ({PLEDGE_CACHE_PATH})")


def fetch_pledge_ratio(years: list[int]) -> dict[tuple[str, int], float]:
    """
    获取大股东质押比例数据。

    降级策略（从优到劣）:
      1. akshare 在线接口（实时最新）
      2. 本地缓存 Parquet（之前成功下载的快照）
      3. 返回空映射（兜底 0.0）

    返回: {(stock_code, report_year): pledge_ratio}
    """
    # 尝试 akshare 在线
    online = _fetch_pledge_from_akshare(years)
    if online:
        _save_pledge_to_cache(online)
        source = online
    else:
        # 回退到缓存
        logger.warning("akshare unavailable, falling back to local cache ...")
        cached = _load_pledge_from_cache()
        if cached:
            source = cached
        else:
            logger.warning("No cache found either, pledge ratio will default to 0.0")
            return {}

    result: dict[tuple[str, int], float] = {}
    for year, mapping in source.items():
        for sc, ratio in mapping.items():
            result[(sc, year)] = ratio
    return result


def _load_turnover_from_cache() -> dict[tuple[str, int], float] | None:
    """从本地缓存加载核心人员变动率"""
    if not TURNOVER_CACHE_PATH.exists():
        return None
    try:
        df = pd.read_parquet(TURNOVER_CACHE_PATH)
        result: dict[tuple[str, int], float] = {}
        for _, row in df.iterrows():
            result[(row["stock_code"], int(row["report_year"]))] = float(row["turnover_rate"])
        logger.info(f"  Loaded {len(result)} turnover records from cache ({TURNOVER_CACHE_PATH})")
        return result
    except Exception as e:
        logger.warning(f"Failed to load turnover cache: {e}")
        return None


def _save_turnover_to_cache(turnover_map: dict[tuple[str, int], float]):
    """将 PDF 解析结果写入本地缓存"""
    rows = [{"stock_code": k[0], "report_year": k[1], "turnover_rate": v}
            for k, v in turnover_map.items()]
    if not rows:
        return
    df = pd.DataFrame(rows)
    TURNOVER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(TURNOVER_CACHE_PATH, index=False)
    logger.info(f"  Saved {len(df)} turnover records to cache ({TURNOVER_CACHE_PATH})")


def fetch_turnover_from_pdf(pdf_base: Path, stock_codes: list[str], years: list[int]) -> dict[tuple[str, int], float]:
    """
    从 PDF 年报提取核心人员变动率。

     降级（从优到劣）:
       1. 本地缓存 Parquet（之前解析的快照）
       2. PDF 现场解析（pdfplumber 提取董监高表格）
       3. 返回 0.0

    返回: {(stock_code, report_year): turnover_rate}
    """
    # 尝试从缓存加载
    cached = _load_turnover_from_cache()
    if cached is not None:
        return cached

    result: dict[tuple[str, int], float] = {}
    for code in stock_codes:
        for year in years:
            pdf_path = pdf_base / code / f"{year}.pdf"
            if not pdf_path.exists():
                continue
            try:
                df = parse_executive_table(pdf_path)
                rate = compute_turnover_rate(df, year)
                result[(code, year)] = rate
                logger.debug(f"  Turnover for {code} {year}: {rate:.1f}%")
            except Exception as e:
                logger.warning(f"  Failed to parse executive table for {code} {year}: {e}")

    if result:
        _save_turnover_to_cache(result)
    return result


def build_financial_records(income_df, balance_df, cashflow_df, stock_codes, years):
    """合并三张报表，构建 financial_annual 记录"""
    records = []
    for code in stock_codes:
        for year in years:
            date_str = f"{year}-12-31"

            def get_val(df, field, default=0.0):
                mask = (df['ts_code'] == code) & (df['report_date'] == date_str)
                rows = df[mask]
                if rows.empty:
                    return default
                val = rows.iloc[0].get(field, default)
                return val if pd.notna(val) else default

            revenue = get_val(income_df, 'ttl_inc_oper')
            cost = get_val(income_df, 'cost_oper')
            gross_profit = revenue - cost
            net_profit = get_val(income_df, 'net_prof')
            non_rec = (get_val(income_df, 'inc_noper') - get_val(income_df, 'exp_noper')
                       + get_val(income_df, 'inc_ast_dspl')
                       + get_val(income_df, 'inc_fv_chg')
                       + get_val(income_df, 'inc_other'))
            ttl_prof_val = get_val(income_df, 'ttl_prof')
            inc_tax = get_val(income_df, 'inc_tax')
            tax_rate = inc_tax / ttl_prof_val if ttl_prof_val > 0 and inc_tax > 0 else 0.15
            deducted = net_profit - non_rec * (1 - tax_rate)
            rd_exp = get_val(income_df, 'exp_rd')
            total_assets = get_val(balance_df, 'ttl_ast')
            net_assets = get_val(balance_df, 'ttl_eqy')
            acct_rcv = get_val(balance_df, 'note_acct_rcv')
            inventory = get_val(balance_df, 'invt')
            goodwill = get_val(balance_df, 'gw')
            ocf = get_val(cashflow_df, 'net_cf_oper')
            capex = get_val(cashflow_df, 'pur_fix_intg_ast')

            roe = net_profit / net_assets if net_assets != 0 else 0.0
            roa = net_profit / total_assets if total_assets != 0 else 0.0
            roic = net_profit / net_assets if net_assets != 0 else 0.0
            gross_margin = gross_profit / revenue if revenue != 0 else 0.0

            records.append((
                code, year,
                round(revenue, 2), round(cost, 2), round(gross_profit, 2),
                round(net_profit, 2), round(deducted, 2), round(rd_exp, 2),
                round(total_assets, 2), round(net_assets, 2),
                round(acct_rcv, 2), round(inventory, 2), round(goodwill, 2),
                round(ocf, 2), round(capex, 2),
                round(roe, 6), round(roa, 6), round(roic, 6), round(gross_margin, 6),
            ))
    return records


def create_database(db_path, stock_codes, years, quantdb_path=None):
    """创建 SQLite 数据库并写入数据"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    base_path = Path(quantdb_path) if quantdb_path else DEFAULT_QUANTDB_PATH
    qdb = _init_quantdb(base_path)

    logger.info("Loading financial data via QuantDatabase path management ...")
    income_df = _load_financial_parquet('income', qdb)
    balance_df = _load_financial_parquet('balance', qdb)
    cashflow_df = _load_financial_parquet('cashflow', qdb)

    stock_basic_path = qdb.meta_path / 'stock_basic.parquet'
    if not stock_basic_path.exists():
        raise FileNotFoundError(f"stock_basic not found: {stock_basic_path}")
    stock_basic = pd.read_parquet(stock_basic_path, engine='pyarrow')

    logger.info(f"Building database for {len(stock_codes)} stocks × {len(years)} years ...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            stock_code TEXT PRIMARY KEY,
            stock_name TEXT NOT NULL,
            industry_sw_level1 TEXT
        )
    """)
    for code in stock_codes:
        match = stock_basic[stock_basic['ts_code'] == code]
        if not match.empty:
            row = match.iloc[0]
            name = str(row.get('name', ''))
            industry = str(row.get('industry_em', ''))
        else:
            name, industry = code, ''
        cursor.execute(
            "INSERT OR REPLACE INTO companies VALUES (?, ?, ?)",
            (code, name, industry)
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_annual (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            revenue REAL, cost_of_revenue REAL, gross_profit REAL,
            net_profit REAL, net_profit_deducted REAL, rd_expenses REAL,
            total_assets REAL, net_assets REAL,
            accounts_receivable REAL, inventory REAL, goodwill REAL,
            operating_cash_flow REAL, capex REAL,
            roe REAL, roa REAL, roic REAL, gross_margin REAL,
            PRIMARY KEY (stock_code, report_year)
        )
    """)

    records = build_financial_records(income_df, balance_df, cashflow_df, stock_codes, years)
    cursor.executemany("""
        INSERT OR REPLACE INTO financial_annual VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    # ── governance_data 表 ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS governance_data (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            audit_opinion TEXT,
            is_standard_audit BOOLEAN,
            major_shareholder_pledge_ratio REAL,
            core_personnel_turnover_rate REAL,
            PRIMARY KEY (stock_code, report_year)
        )
    """)

    # 获取质押比例数据（akshare → 本地缓存 → 兜底 0.0）
    logger.info("Fetching pledge ratio ...")
    pledge_map = fetch_pledge_ratio(years)
    logger.info(f"  Got {len(pledge_map)} pledge ratio records")

    # 从 PDF 年报获取核心人员变动率（优先 PDF → 降级 0.0）
    pdf_base = Path("data/raw/annual_reports")
    logger.info("Fetching executive turnover from PDF (if available) ...")
    turnover_map = fetch_turnover_from_pdf(pdf_base, stock_codes, years)

    gov_records = []
    for code in stock_codes:
        for year in years:
            ratio = pledge_map.get((code, year), 0.0)
            tover = turnover_map.get((code, year), 0.0)
            gov_records.append((code, year, ratio, '标准无保留意见', True, tover))

    cursor.executemany("""
        INSERT OR REPLACE INTO governance_data
        (stock_code, report_year, major_shareholder_pledge_ratio, audit_opinion, is_standard_audit, core_personnel_turnover_rate)
        VALUES (?, ?, ?, ?, ?, ?)
    """, gov_records)

    conn.commit()
    conn.close()

    logger.info(f"Database created: {db_path}")
    logger.info(f"  Companies: {len(stock_codes)}")
    logger.info(f"  Financial records: {len(records)}")
    logger.info(f"  Governance records: {len(gov_records)}")
    return records


def get_sample_stocks(quantdb_path, n):
    """从 stock_basic 中随机选取 n 只股票"""
    qdb = _init_quantdb(quantdb_path)
    fp = qdb.meta_path / 'stock_basic.parquet'
    if not fp.exists():
        raise FileNotFoundError(f"stock_basic not found: {fp}")
    df = pd.read_parquet(fp, engine='pyarrow')
    candidates = df[~df['ts_code'].str.contains('300', na=False)].copy()
    selected = candidates.sample(min(n, len(candidates))).sort_values('ts_code')
    return selected['ts_code'].tolist()


def main():
    parser = argparse.ArgumentParser(description='quant_DB → FSG-Quant 数据桥接')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT_DB),
                        help=f'输出 SQLite 路径 (default: {DEFAULT_OUTPUT_DB})')
    parser.add_argument('--sample', type=int, default=5,
                        help='随机选取 N 只股票 (与 --stocks 互斥)')
    parser.add_argument('--stocks', nargs='+', default=None,
                        help='指定股票代码列表，如 000001.SZ 600519.SH')
    parser.add_argument('--years', nargs='+', type=int, default=[2021, 2022, 2023],
                        help='报告年份列表 (default: 2021 2022 2023)')
    parser.add_argument('--quantdb-path', default=str(DEFAULT_QUANTDB_PATH),
                        help=f'quant_DB 根路径')

    args = parser.parse_args()

    years = sorted(set(args.years))
    if args.stocks:
        stock_codes = args.stocks
    else:
        stock_codes = get_sample_stocks(args.quantdb_path, args.sample)

    logger.info(f"Stock codes: {stock_codes}")
    logger.info(f"Report years: {years}")
    logger.info(f"Output: {args.output}")

    create_database(args.output, stock_codes, years, quantdb_path=args.quantdb_path)

    print(f"\n桥接完成！数据库已写入: {args.output}")
    print(f"  股票数: {len(stock_codes)}")
    print(f"  年份: {years}")
    print(f"\n现在可以运行: python -m pytest tests/ -v")


if __name__ == '__main__':
    main()
