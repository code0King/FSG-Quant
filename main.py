"""
主程序入口

整合所有模块，提供完整的量化分析流程：
1. 数据加载
2. L1/L2/L3因子计算
3. 因子合成与打分
4. 回测分析

使用方式：
    python main.py
    
或在Jupyter Notebook中导入使用：
    from main import run_full_analysis
    result = run_full_analysis('000001.SZ', 2023)
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_pipeline.data_loader import DataLoader
from nlp.commitment_parser import CommitmentParser
from nlp.finbert_analyzer import FinBERTAnalyzer
from factors.L1_performance import L1PerformanceFactor
from factors.L2_strategy import L2StrategyFactor
from factors.L3_governance import L3GovernanceFactor
from factors.factor_synthesizer import FactorSynthesizer
from backtest.backtest_engine import BacktestEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/analysis.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def run_single_stock_analysis(stock_code: str, year: int) -> Dict:
    """
    对单只股票进行全方位分析
    
    Args:
        stock_code: 股票代码（如'000001.SZ'）
        year: 分析年份
        
    Returns:
        包含所有分析结果的字典
    """
    logger.info(f"开始分析 {stock_code} {year}年")
    
    # 初始化组件
    loader = DataLoader()
    
    # L1: 业绩验证层
    logger.info("计算L1业绩验证因子...")
    l1_calculator = L1PerformanceFactor(data_loader=loader)
    l1_result = l1_calculator.calculate_all(stock_code, year)
    
    if not l1_result:
        logger.warning(f"L1因子计算失败: {stock_code}")
        return {'error': 'L1 factor calculation failed'}
    
    logger.info(f"L1完成 - ROE: {l1_result.get('roe')}, 盈利质量: {l1_result.get('profit_quality_score')}")
    
    # L2: 战略执行层（需要NLP组件）
    logger.info("计算L2战略执行因子...")
    try:
        parser = CommitmentParser()
        # 注意：FinBERT需要torch，如果未安装会报错
        try:
            analyzer = FinBERTAnalyzer()
            l2_calculator = L2StrategyFactor(
                data_loader=loader,
                commitment_parser=parser,
                finbert_analyzer=analyzer
            )
            l2_result = l2_calculator.calculate_all(stock_code, year)
            logger.info(f"L2完成 - 战略执行评分: {l2_result.get('strategy_execution_score')}")
        except ImportError as e:
            logger.warning(f"FinBERT未安装，跳过情绪分析: {str(e)}")
            l2_result = {'error': 'FinBERT not available'}
    except Exception as e:
        logger.error(f"L2因子计算失败: {str(e)}")
        l2_result = {'error': str(e)}
    
    # L3: 治理排雷层
    logger.info("计算L3治理排雷因子...")
    l3_calculator = L3GovernanceFactor(data_loader=loader)
    l3_result = l3_calculator.calculate_all(stock_code, year)
    
    if l3_result:
        logger.info(f"L3完成 - 风险等级: {l3_result.get('governance_risk_level')}")
    else:
        logger.warning("L3因子计算失败")
    
    # 综合结果
    result = {
        'stock_code': stock_code,
        'year': year,
        'L1_performance': l1_result,
        'L2_strategy': l2_result,
        'L3_governance': l3_result
    }
    
    logger.info(f"分析完成: {stock_code}")
    return result


def run_portfolio_analysis(year: int, strategy: str = 'offensive', top_n: int = 10) -> Dict:
    """
    对整个投资组合进行分析
    
    Args:
        year: 分析年份
        strategy: 策略类型（'offensive'或'defensive'）
        top_n: 选股数量
        
    Returns:
        包含组合分析结果的字典
    """
    logger.info(f"开始组合分析 - 年份: {year}, 策略: {strategy}, 选股数: {top_n}")
    
    # 初始化组件
    loader = DataLoader()
    
    # 因子合成
    logger.info("合成因子并计算打分卡...")
    synthesizer = FactorSynthesizer(data_loader=loader)
    scores_df = synthesizer.calculate_all(year)
    
    if scores_df.empty:
        logger.warning("没有可用的综合评分数据")
        return {'error': 'No composite scores available'}
    
    logger.info(f"获得 {len(scores_df)} 只股票的评分")
    
    # 回测
    logger.info("执行回测分析...")
    backtest_engine = BacktestEngine(data_loader=loader)
    backtest_result = backtest_engine.run_annual_rebalancing(
        start_year=year,
        end_year=year,
        strategy=strategy,
        top_n=top_n
    )
    
    # 综合结果
    result = {
        'year': year,
        'strategy': strategy,
        'scores_summary': {
            'total_stocks': len(scores_df),
            'avg_offensive_score': scores_df['offensive_score'].mean(),
            'avg_defensive_score': scores_df['defensive_score'].mean(),
            'risk_distribution': scores_df['composite_risk_level'].value_counts().to_dict()
        },
        'backtest_result': backtest_result
    }
    
    logger.info("组合分析完成")
    return result


def run_full_analysis(stock_code: Optional[str] = None, year: int = 2023) -> Dict:
    """
    运行完整的全方位分析
    
    Args:
        stock_code: 股票代码（可选，不提供则分析整个组合）
        year: 分析年份
        
    Returns:
        分析结果字典
    """
    logger.info("=" * 60)
    logger.info("A股上市公司全方位量化分析框架")
    logger.info("=" * 60)
    
    if stock_code:
        # 单只股票分析
        return run_single_stock_analysis(stock_code, year)
    else:
        # 组合分析
        return run_portfolio_analysis(year)


def main():
    """
    主函数 - 命令行入口
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='A股上市公司全方位量化分析框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析单只股票
  python main.py --stock 000001.SZ --year 2023
  
  # 分析整个组合（进攻型策略）
  python main.py --year 2023 --strategy offensive --top-n 10
  
  # 分析整个组合（防御型策略）
  python main.py --year 2023 --strategy defensive --top-n 10
        """
    )
    
    parser.add_argument('--stock', type=str, help='股票代码（如000001.SZ）')
    parser.add_argument('--year', type=int, default=2023, help='分析年份（默认2023）')
    parser.add_argument('--strategy', type=str, default='offensive', 
                       choices=['offensive', 'defensive'],
                       help='策略类型（默认offensive）')
    parser.add_argument('--top-n', type=int, default=10, help='选股数量（默认10）')
    
    args = parser.parse_args()
    
    try:
        if args.stock:
            # 单只股票分析
            result = run_single_stock_analysis(args.stock, args.year)
            
            print("\n" + "=" * 60)
            print(f"分析结果: {args.stock} ({args.year}年)")
            print("=" * 60)
            
            if 'error' in result:
                print(f"错误: {result['error']}")
            else:
                print("\n【L1 业绩验证】")
                l1 = result.get('L1_performance', {})
                print(f"  ROE: {l1.get('roe', 'N/A')}")
                print(f"  ROA: {l1.get('roa', 'N/A')}")
                print(f"  ROIC: {l1.get('roic', 'N/A')}")
                print(f"  毛利率等级: {l1.get('gross_margin_grade', 'N/A')}")
                print(f"  盈利质量评分: {l1.get('profit_quality_score', 'N/A')}")
                print(f"  预警标记: {l1.get('warning_flags', [])}")
                
                print("\n【L2 战略执行】")
                l2 = result.get('L2_strategy', {})
                if 'error' not in l2:
                    print(f"  营收兑现率: {l2.get('revenue_fulfillment_rate', 'N/A')}")
                    print(f"  利润兑现率: {l2.get('profit_fulfillment_rate', 'N/A')}")
                    print(f"  管理层情绪: {l2.get('management_sentiment', 'N/A')}")
                    print(f"  战略执行评分: {l2.get('strategy_execution_score', 'N/A')}")
                else:
                    print(f"  未计算: {l2.get('error')}")
                
                print("\n【L3 治理排雷】")
                l3 = result.get('L3_governance', {})
                print(f"  股权质押比例: {l3.get('pledge_ratio', 'N/A')}%")
                print(f"  审计意见: {l3.get('audit_opinion', 'N/A')}")
                print(f"  高管流失率: {l3.get('executive_turnover', 'N/A')}%")
                print(f"  风险等级: {l3.get('governance_risk_level', 'N/A')}")
                
        else:
            # 组合分析
            result = run_portfolio_analysis(args.year, args.strategy, args.top_n)
            
            print("\n" + "=" * 60)
            print(f"组合分析结果 ({args.year}年, {args.strategy}策略)")
            print("=" * 60)
            
            if 'error' in result:
                print(f"错误: {result['error']}")
            else:
                summary = result.get('scores_summary', {})
                print(f"\n股票总数: {summary.get('total_stocks', 0)}")
                print(f"平均进攻型评分: {summary.get('avg_offensive_score', 0):.2f}")
                print(f"平均防御型评分: {summary.get('avg_defensive_score', 0):.2f}")
                
                print("\n风险等级分布:")
                for level, count in summary.get('risk_distribution', {}).items():
                    print(f"  {level}: {count}只")
                
                backtest = result.get('backtest_result', {})
                metrics = backtest.get('performance_metrics', {})
                
                print("\n【回测绩效指标】")
                print(f"  总收益: {metrics.get('total_return', 0)*100:.2f}%")
                print(f"  年化收益: {metrics.get('annualized_return', 0)*100:.2f}%")
                print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
                print(f"  最大回撤: {metrics.get('max_drawdown', 0)*100:.2f}%")
                print(f"  胜率: {metrics.get('win_rate', 0)*100:.2f}%")
        
        print("\n" + "=" * 60)
        logger.info("分析完成")
        
    except Exception as e:
        logger.error(f"分析失败: {str(e)}", exc_info=True)
        print(f"\n错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
