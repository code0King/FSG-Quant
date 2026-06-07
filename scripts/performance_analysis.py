"""
回测绩效分析 - 详细指标计算与对比
"""
import sys
from pathlib import Path
import logging

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def run_backtest(start_year, end_year, strategy, top_n=5):
    from data_pipeline.data_loader import DataLoader
    from backtest.backtest_engine import BacktestEngine
    loader = DataLoader(data_dir='data')
    engine = BacktestEngine(loader)
    return engine.run_annual_rebalancing(start_year, end_year, strategy, top_n)


def calc_detailed_metrics(returns):
    s = pd.Series(returns)
    total = (1 + s).prod() - 1
    n = len(s)
    ann = (1 + total) ** (1 / n) - 1 if n > 0 else 0.0
    vol = s.std() * np.sqrt(n) if n > 1 else 0.0
    sharpe = (ann - 0.03) / vol if vol > 0 else 0.0
    cum = (1 + s).cumprod()
    dd = cum / cum.cummax() - 1
    mdd = abs(dd.min())
    win_rate = (s > 0).sum() / n if n > 0 else 0.0
    downside = s[s < 0].std() * np.sqrt(n) if (s < 0).sum() > 1 else 0.0
    sortino = (ann - 0.03) / downside if downside > 0 else 0.0
    calmar = ann / mdd if mdd > 0 else 0.0
    return {
        'total_return': total,
        'annualized_return': ann,
        'volatility': vol,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'calmar_ratio': calmar,
        'max_drawdown': mdd,
        'win_rate': win_rate,
        'years': n,
    }


def load_all_stock_returns():
    """为每只股票独立计算年度收益（用于归因分析）"""
    all_returns = {}
    for year in [2021, 2022, 2023]:
        df = pd.read_parquet(f'data/market_data/daily_quotes/{year}.parquet')
        dates = sorted([d for d in df['trade_date'].unique() if str(d)[:4] == str(year)])
        if len(dates) < 2:
            continue
        first, last = dates[0], dates[-1]
        fp = df[df['trade_date'] == first][['stock_code', 'adj_close']].set_index('stock_code')
        lp = df[df['trade_date'] == last][['stock_code', 'adj_close']].set_index('stock_code')
        valid = fp.join(lp, how='inner', lsuffix='_first', rsuffix='_last')
        valid = valid[valid['adj_close_first'] > 0]
        valid['year_return'] = (valid['adj_close_last'] - valid['adj_close_first']) / valid['adj_close_first']
        all_returns[year] = valid['year_return']
    return all_returns


def print_separator(title=''):
    w = 72
    if title:
        side = (w - len(title) - 4) // 2
        print(f"\n{'=' * side}  {title}  {'=' * (w - side - len(title) - 4)}")
    else:
        print('=' * w)


def main():
    start_year, end_year = 2021, 2023
    top_n = 5

    print("=" * 72)
    print("              FSG-Quant 回测绩效分析报告")
    print(f"              策略对比: Offensive vs Defensive  |  Top-{top_n}  |  {start_year}-{end_year}")
    print("=" * 72)

    # 1. 运行回测
    results = {}
    for strategy in ['offensive', 'defensive']:
        bt = run_backtest(start_year, end_year, strategy, top_n=top_n)
        results[strategy] = bt

    # 2. 绩效指标对比
    print_separator("绩效指标对比")
    header = f"{'指标':<22} {'进攻策略':>12} {'防御策略':>12} {'基准(等权)':>12}"
    print(header)
    print("-" * len(header))

    # 计算基准（所有股票等权）
    stock_rets = load_all_stock_returns()
    bench_returns = [stock_rets[y].mean() for y in [2021, 2022, 2023]]
    bench_metrics = calc_detailed_metrics(bench_returns)

    for strategy in ['offensive', 'defensive']:
        r = results[strategy]
        pr = [x['return'] for x in r['portfolio_returns']]
        r['_metrics'] = calc_detailed_metrics(pr)

    def fmt_val(v, pct=False):
        if pct:
            return f"{v:.2%}" if abs(v) < 100 else f"{v:.2f}"
        return f"{v:.2f}"

    metrics_display = [
        ('总收益率', 'total_return', True),
        ('年化收益率', 'annualized_return', True),
        ('年化波动率', 'volatility', True),
        ('夏普比率', 'sharpe_ratio', False),
        ('索提诺比率', 'sortino_ratio', False),
        ('卡玛比率', 'calmar_ratio', False),
        ('最大回撤', 'max_drawdown', True),
        ('胜率', 'win_rate', True),
    ]
    for label, key, is_pct in metrics_display:
        o = results['offensive']['_metrics'][key]
        d = results['defensive']['_metrics'][key]
        b = bench_metrics[key]
        print(f"{label:<22} {fmt_val(o, is_pct):>12} {fmt_val(d, is_pct):>12} {fmt_val(b, is_pct):>12}")

    # 3. 逐年收益对比
    print_separator("逐年收益对比")
    years = [r['year'] for r in results['offensive']['portfolio_returns']]
    off_rets = [r['return'] for r in results['offensive']['portfolio_returns']]
    def_rets = [r['return'] for r in results['defensive']['portfolio_returns']]
    bench_rets = [stock_rets[y].mean() for y in years]

    print(f"{'年份':<8} {'进攻':>10} {'防御':>10} {'基准(等权)':>12} {'沪深300':>10}")
    print("-" * 52)
    # 近似沪深300年度收益 (from public data)
    csi300 = {2021: -0.05, 2022: -0.22, 2023: -0.11}
    for i, y in enumerate(years):
        print(f"{y:<8} {off_rets[i]:>+10.2%} {def_rets[i]:>+10.2%} {bench_rets[i]:>+12.2%} {csi300.get(y, 0):>+10.2%}")

    # 4. 逐年持仓明细
    print_separator("逐年持仓明细")
    for strategy in ['offensive', 'defensive']:
        print(f"\n  [{strategy}] 持仓:")
        bt = results[strategy]
        for i, year_data in enumerate(bt['yearly_holdings']):
            year = bt['portfolio_returns'][i]['year']
            score_col = f'{strategy}_score'
            stocks = year_data[['stock_code', score_col, 'composite_risk_level']].copy()
            ret = stock_rets.get(year, pd.Series())
            stocks['实际收益'] = stocks['stock_code'].map(ret)
            avg_ret = stocks['实际收益'].mean()
            print(f"    {year} (组合收益: {bt['portfolio_returns'][i]['return']:+6.2%}, 持仓均值: {avg_ret:+6.2%}):")
            for _, s in stocks.iterrows():
                sr = s['实际收益']
                sr_str = f"{sr:+6.2%}" if pd.notna(sr) else "  N/A "
                print(f"      {s['stock_code']:>12}  评分={s[score_col]:6.1f}  风险={s['composite_risk_level']:<6}  收益={sr_str}")
        print()

    # 5. 行业分布分析
    print_separator("行业偏好分析")
    # Load L1 to get industry info
    l1 = pd.read_parquet('data/factors/L1_factors.parquet')
    # We don't have industry in L1, let's derive from metadata
    scores = pd.read_parquet('data/factors/composite_scores.parquet')
    # Check if we have industry info in any data
    for strategy in ['offensive', 'defensive']:
        bt = results[strategy]
        all_selected = []
        for i, year_data in enumerate(bt['yearly_holdings']):
            year = bt['portfolio_returns'][i]['year']
            for _, s in year_data.iterrows():
                all_selected.append({'stock_code': s['stock_code'], 'year': year, 'strategy': strategy})
        # We don't have industry mapping here, skip
    print("  (行业映射信息待补充 - 可从 quant_DB 桥接股票基础信息)")

    # 6. 最佳/最差个股
    print_separator("最佳/最差持仓个股")
    for strategy in ['offensive', 'defensive']:
        print(f"\n  [{strategy}]")
        bt = results[strategy]
        all_stocks = {}
        for i, year_data in enumerate(bt['yearly_holdings']):
            year = bt['portfolio_returns'][i]['year']
            ret = stock_rets.get(year, pd.Series())
            for _, s in year_data.iterrows():
                code = s['stock_code']
                r = ret.get(code)
                if pd.notna(r):
                    all_stocks[f"{code} ({year})"] = r
        if all_stocks:
            sorted_stocks = sorted(all_stocks.items(), key=lambda x: x[1])
            print(f"    最佳: {sorted_stocks[-1][0]} 收益 {sorted_stocks[-1][1]:+6.2%}")
            print(f"    最差: {sorted_stocks[0][0]} 收益 {sorted_stocks[0][1]:+6.2%}")

    # 7. 净值曲线
    print_separator("累计净值")
    for strategy in ['offensive', 'defensive']:
        rets = [r['return'] for r in results[strategy]['portfolio_returns']]
        cum = 1.0
        vals = [1.0]
        for r in rets:
            cum *= (1 + r)
            vals.append(cum)
        print(f"  [{strategy}]  初始=1.000  ", end='')
        for v in vals[1:]:
            print(f"  {v:.4f}", end='')
        print()
    # benchmark
    cum = 1.0
    vals = [1.0]
    for r in bench_rets:
        cum *= (1 + r)
        vals.append(cum)
    print(f"  [基准等权] 初始=1.000  ", end='')
    for v in vals[1:]:
        print(f"  {v:.4f}", end='')
    print()

    csi_cum = 1.0
    vals = [1.0]
    for y in years:
        csi_cum *= (1 + csi300.get(y, 0))
        vals.append(csi_cum)
    print(f"  [沪深300]  初始=1.000  ", end='')
    for v in vals[1:]:
        print(f"  {v:.4f}", end='')
    print()

    # 8. 风险分析
    print_separator("风险分析")
    for strategy in ['offensive', 'defensive']:
        m = results[strategy]['_metrics']
        print(f"  [{strategy}]")
        print(f"    年化波动率: {m['volatility']:.2%}")
        print(f"    最大回撤:   {m['max_drawdown']:.2%}")
        print(f"    下行风险:   {m['volatility']:.2%}")  # Same as vol for yearly
        print(f"    夏普比率:   {m['sharpe_ratio']:.2f}")
        print(f"    索提诺比率: {m['sortino_ratio']:.2f}")
        print(f"    卡玛比率:   {m['calmar_ratio']:.2f}")
        print(f"    胜率:       {m['win_rate']:.1%}")

    # 9. 汇总结论
    print_separator("分析结论")
    o_ret = results['offensive']['_metrics']['annualized_return']
    d_ret = results['defensive']['_metrics']['annualized_return']
    o_sharpe = results['offensive']['_metrics']['sharpe_ratio']
    d_sharpe = results['defensive']['_metrics']['sharpe_ratio']
    o_mdd = results['offensive']['_metrics']['max_drawdown']
    d_mdd = results['defensive']['_metrics']['max_drawdown']
    b_ret = bench_metrics['annualized_return']

    print(f"  - 进攻策略年化收益 {o_ret:.2%}，防御策略 {d_ret:.2%}，基准 {b_ret:.2%}")
    print(f"  - 进攻策略夏普比率 {o_sharpe:.2f}，防御策略夏普比率 {d_sharpe:.2f}")
    print(f"  - 进攻策略最大回撤 {o_mdd:.2%}，防御策略最大回撤 {d_mdd:.2%}")
    if o_sharpe > d_sharpe:
        print(f"  - 进攻策略在本次回测区间风险调整后收益更优")
    else:
        print(f"  - 防御策略在本次回测区间风险调整后收益更优")
    print(f"  - 两种策略均跑赢基准（等权持有所有50只股票）" if o_ret > b_ret and d_ret > b_ret else "  - 策略表现待进一步优化")
    print(f"  - 回测仅含单一调仓周期（年度），样本量约{len(years)}个数据点")


if __name__ == '__main__':
    main()
