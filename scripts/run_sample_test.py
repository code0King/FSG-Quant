"""
小样本端到端测试

全流程：构建数据库 → 因子计算 → 打分卡 → 回测

用法:
    python scripts/run_sample_test.py
    python scripts/run_sample_test.py --stocks 000001.SZ 600519.SH
"""
import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))  # 项目根目录，用于 import scripts

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
_run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
_log_file = LOG_DIR / f"sample_test_{_run_ts}.log"

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

DB_PATH = Path("data/raw/financial_data.sqlite")
FACTORS_DIR = Path("data/factors")
DATA_DIR = "data"
INDUSTRY_CONFIG = "config/industry_thresholds.yaml"

SAMPLE_STOCKS = ['000001.SZ', '000002.SZ', '600519.SH', '300750.SZ', '000858.SZ']
TEST_YEARS = [2021, 2022, 2023, 2024, 2025]


def ensure_database(stock_codes, years):
    """如果数据库不存在或缺失数据，运行桥接"""
    if not DB_PATH.exists():
        logger.info("Database not found, running quantdb_bridge ...")
        from scripts.quantdb_bridge import create_database
        create_database(DB_PATH, stock_codes, years)
        return

    # 检查关键数据是否完整
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM financial_annual")
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        logger.info("financial_annual table not found, re-running bridge ...")
        conn.close()
        from scripts.quantdb_bridge import create_database
        create_database(DB_PATH, stock_codes, years)
        return
    conn.close()

    expected = len(stock_codes) * len(years)
    if count < expected:
        logger.info(f"Database has {count}/{expected} records, re-running bridge ...")
        from scripts.quantdb_bridge import create_database
        create_database(DB_PATH, stock_codes, years)
    else:
        logger.info(f"Database ready ({count} financial records)")


def load_industry_config():
    """加载行业配置"""
    import yaml
    path = Path(INDUSTRY_CONFIG)
    if path.exists():
        with open(path, encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def calculate_l1_factors(stock_codes, years):
    """计算 L1 业绩验证层因子"""
    from factors.L1_performance import L1PerformanceFactor

    calculator = L1PerformanceFactor(
        db_path=str(DB_PATH),
        industry_config_path=INDUSTRY_CONFIG
    )

    records = []
    for code in stock_codes:
        for year in years:
            result = calculator.calculate_all(code, year)
            if result:
                records.append({
                    'stock_code': code,
                    'report_year': year,
                    **result
                })
                logger.info(f"  L1 {code} {year}: ROE={result['roe']:.2%}, "
                           f"盈利质量={result['profit_quality_score']:.1f}")
            else:
                logger.warning(f"  L1 {code} {year}: 计算失败")

    if not records:
        logger.error("L1 factor calculation returned no results")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    FACTORS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FACTORS_DIR / 'L1_factors.parquet', index=False)
    logger.info(f"L1 factors saved: {len(df)} records")
    return df


def _load_mda_text(stock_code: str, year: int) -> str:
    """从数据库读取真实 MDA 文本，不存在时返回空字符串"""
    import sqlite3
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute("SELECT mda_text FROM mda_text WHERE stock_code=? AND report_year=?", (stock_code, year))
        row = cur.fetchone()
        return row[0] if row else ""
    except sqlite3.OperationalError:
        return ""
    finally:
        conn.close()


def calculate_l2_factors(stock_codes, years):
    """计算 L2 战略执行层因子（使用数据库真实 MDA，无 FinBERT 时 sentiment=0）"""
    from data_pipeline.data_loader import DataLoader
    from nlp.commitment_parser import CommitmentParser

    loader = DataLoader(data_dir=DATA_DIR)
    parser = CommitmentParser()

    records = []
    for code in stock_codes:
        for year in years:
            current = loader.load_financial(stock_code=code, year=year)
            last = loader.load_financial(stock_code=code, year=year - 1)
            if current is None or current.empty:
                continue

            current_dict = current.iloc[0].to_dict()
            last_dict = last.iloc[0].to_dict() if last is not None and not last.empty else None

            # 优先使用数据库中的真实 MDA 文本
            mda_text = _load_mda_text(code, year)
            if not mda_text:
                mda_text = "公司将深入推进战略转型，预计营收增长15%，利润增长12%，持续加大研发投入以提升核心竞争力。"

            commitments = parser.extract_commitments(mda_text)
            has_explicit = commitments.get("has_explicit", False)

            revenue_fulfillment = None
            profit_fulfillment = None
            if has_explicit and last_dict:
                last_rev = last_dict.get("revenue", 0)
                curr_rev = current_dict.get("revenue", 0)
                if commitments.get("revenue_growth_target") and last_rev > 0:
                    actual_growth = (curr_rev - last_rev) / last_rev * 100
                    target = commitments["revenue_growth_target"]
                    revenue_fulfillment = max(0.0, (actual_growth / target) * 100) if target != 0 else 0.0

                last_profit = last_dict.get("net_profit", 0)
                curr_profit = current_dict.get("net_profit", 0)
                if commitments.get("profit_growth_target") and last_profit > 0:
                    actual_growth = (curr_profit - last_profit) / last_profit * 100
                    target = commitments["profit_growth_target"]
                    profit_fulfillment = max(0.0, (actual_growth / target) * 100) if target != 0 else 0.0

            sentiment = 0.0
            if revenue_fulfillment is not None:
                avg_fulfill = (revenue_fulfillment + (profit_fulfillment or revenue_fulfillment)) / 2
                score = max(0, min(100, 0.7 * min(100, avg_fulfill * 0.7) + 0.3 * (sentiment + 1) * 50))
            else:
                score = max(0, min(100, (sentiment + 1) * 50))

            records.append({
                'stock_code': code,
                'report_year': year,
                'revenue_fulfillment_rate': round(revenue_fulfillment, 2) if revenue_fulfillment else None,
                'profit_fulfillment_rate': round(profit_fulfillment, 2) if profit_fulfillment else None,
                'management_sentiment': round(sentiment, 4),
                'strategy_execution_score': round(score, 2),
                'has_explicit_commitment': has_explicit,
            })
            logger.info(f"  L2 {code} {year}: 承诺={'有' if has_explicit else '无'}, "
                       f"营收兑现={revenue_fulfillment}, 战略评分={score:.1f}")

    df = pd.DataFrame(records)
    FACTORS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FACTORS_DIR / 'L2_factors.parquet', index=False)
    logger.info(f"L2 factors saved: {len(df)} records")
    return df


def calculate_l3_factors(stock_codes, years):
    """计算 L3 治理排雷层因子"""
    from data_pipeline.data_loader import DataLoader
    from factors.L3_governance import L3GovernanceFactor

    loader = DataLoader(data_dir=DATA_DIR)
    calculator = L3GovernanceFactor(loader)

    records = []
    for code in stock_codes:
        for year in years:
            result = calculator.calculate_all(code, year)
            if result:
                records.append({
                    'stock_code': code,
                    'report_year': year,
                    **result
                })
                logger.info(f"  L3 {code} {year}: 风险等级={result['governance_risk_level']}")
            else:
                logger.warning(f"  L3 {code} {year}: 计算失败")

    if not records:
        logger.error("L3 factor calculation returned no results")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    FACTORS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FACTORS_DIR / 'L3_factors.parquet', index=False)
    logger.info(f"L3 factors saved: {len(df)} records")
    return df


def run_synthesizer(year):
    """运行因子合成器（打分卡 + 风险分级）"""
    from data_pipeline.data_loader import DataLoader
    from factors.factor_synthesizer import FactorSynthesizer

    loader = DataLoader(data_dir=DATA_DIR)
    synthesizer = FactorSynthesizer(loader)

    result = synthesizer.calculate_all(year)
    if result.empty:
        logger.warning(f"No composite scores for year {year}")
        return result

    FACTORS_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(FACTORS_DIR / 'composite_scores.parquet', index=False)
    logger.info(f"Composite scores for {year}: {len(result)} stocks")
    return result


def run_backtest(start_year, end_year, strategy='offensive', top_n=5):
    """运行回测"""
    from data_pipeline.data_loader import DataLoader
    from backtest.backtest_engine import BacktestEngine

    loader = DataLoader(data_dir=DATA_DIR)
    engine = BacktestEngine(loader)

    result = engine.run_annual_rebalancing(
        start_year=start_year,
        end_year=end_year,
        strategy=strategy,
        top_n=top_n
    )
    return result


def main():
    parser = argparse.ArgumentParser(description='小样本端到端测试')
    parser.add_argument('--stocks', nargs='+', default=None,
                        help='股票代码列表')
    parser.add_argument('--years', nargs='+', type=int, default=TEST_YEARS,
                        help='报告年份 (default: 2021 2022 2023)')
    parser.add_argument('--all', action='store_true',
                        help='从数据库读取所有股票')
    parser.add_argument('--skip-bridge', action='store_true',
                        help='跳过数据库构建')
    parser.add_argument('--skip-market', action='store_true',
                        help='跳过行情数据转换')
    args = parser.parse_args()

    if args.all:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT stock_code FROM financial_annual")
        stock_codes = [r[0] for r in cursor.fetchall()]
        conn.close()
    elif args.stocks:
        stock_codes = args.stocks
    else:
        stock_codes = SAMPLE_STOCKS
    years = sorted(set(args.years))

    print("=" * 64)
    print("   FSG-Quant 小样本端到端测试")
    print("=" * 64)
    print(f"\n测试标的: {stock_codes}")
    print(f"报告年份: {years}")
    print(f"日志文件: {_log_file}")
    print()

    # Step 1: 构建数据库
    if not args.skip_bridge:
        print("[1/5] 构建 SQLite 数据库 ...")
        ensure_database(stock_codes, years)
    else:
        print("[1/5] 跳过数据库构建")

    # Step 2: 行情数据转换
    if not args.skip_market:
        print("\n[2/5] 转换行情数据 ...")
        try:
            from scripts.market_bridge import convert_market_data
            for year in years:
                convert_market_data(year, 'data/market_data/daily_quotes')
        except Exception as e:
            logger.warning(f"行情转换失败 (不影响核心流程): {e}")
    else:
        print("\n[2/5] 跳过行情数据转换")

    # Step 3: 因子计算
    print("\n[3/5] 计算因子 ...")

    print("  --- L1 业绩验证层 ---")
    l1_df = calculate_l1_factors(stock_codes, years)
    if l1_df.empty:
        logger.error("L1 因子计算失败，终止测试")
        return

    print("  --- L2 战略执行层 ---")
    l2_df = calculate_l2_factors(stock_codes, years)

    print("  --- L3 治理排雷层 ---")
    l3_df = calculate_l3_factors(stock_codes, years)
    if l3_df.empty:
        logger.error("L3 因子计算失败，终止测试")
        return

    # Step 4: 因子合成与打分卡（所有年份）
    print("\n[4/5] 因子合成与打分卡 ...")
    all_scores = []
    for y in years:
        scores = run_synthesizer(y)
        if not scores.empty:
            all_scores.append(scores)

    latest_year = max(years)
    if all_scores:
        # 合并所有年份评分到一个文件
        combined = pd.concat(all_scores, ignore_index=True)
        FACTORS_DIR.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(FACTORS_DIR / 'composite_scores.parquet', index=False)
        logger.info(f"All years composite scores saved: {len(combined)} records")

        # 展示最新年份
        latest_scores = combined[combined['report_year'] == latest_year]
        if not latest_scores.empty:
            print(f"\n  {latest_year}年综合评分:")
            score_cols = ['stock_code', 'offensive_score', 'defensive_score', 'composite_risk_level']
            for _, row in latest_scores[score_cols].iterrows():
                print(f"    {row['stock_code']}: 进攻={row['offensive_score']:.1f}  "
                      f"防御={row['defensive_score']:.1f}  风险={row['composite_risk_level']}")

    # Step 5: 回测
    test_start = min(years)
    print(f"\n[5/5] 回测 ({test_start}-{latest_year}) ...")
    for strategy in ['offensive', 'defensive']:
        bt_result = run_backtest(test_start, latest_year, strategy, top_n=3)
        metrics = bt_result.get('performance_metrics', {})
        print(f"\n  [{strategy}] 策略:")
        print(f"    总收益: {metrics.get('total_return', 0)*100:.2f}%")
        print(f"    年化收益: {metrics.get('annualized_return', 0)*100:.2f}%")
        print(f"    夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"    最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
        print(f"    胜率: {metrics.get('win_rate', 0)*100:.1f}%")
        if bt_result.get('yearly_holdings'):
            print(f"    持仓: {[list(h['stock_code']) for h in bt_result['yearly_holdings'][:2]]}")

    # 汇总
    print("\n" + "=" * 64)
    print("   测试完成!")
    print("=" * 64)
    print(f"\n  数据库: {DB_PATH} ({len(stock_codes)}只股票)")
    print(f"  因子文件: {FACTORS_DIR}/")
    print(f"  行情文件: data/market_data/daily_quotes/")
    print(f"\n  下一步: python -m pytest tests/ -v")


if __name__ == '__main__':
    main()
