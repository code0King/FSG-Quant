"""
回测引擎

基于Qlib框架实现年度调仓策略的回测，包括：
1. 因子数据转换为Qlib格式
2. 年度调仓策略执行
3. 绩效指标计算（收益率、夏普比率、最大回撤等）

使用示例：
    >>> from data_pipeline.data_loader import DataLoader
    >>> 
    >>> loader = DataLoader()
    >>> engine = BacktestEngine(loader)
    >>> result = engine.run_annual_rebalancing(2020, 2023, 'offensive', top_n=10)
    >>> print(result['performance_metrics'])
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    回测引擎
    
    实现基于打分卡的年度调仓策略回测。
    
    Attributes:
        data_loader: 数据加载器实例
        risk_free_rate: 无风险利率（年化）
    """
    
    def __init__(self, data_loader, risk_free_rate: float = 0.03):
        """
        初始化回测引擎
        
        Args:
            data_loader: DataLoader实例
            risk_free_rate: 无风险利率，默认3%
        """
        self.data_loader = data_loader
        self.risk_free_rate = risk_free_rate
        
        logger.info(f"BacktestEngine initialized (risk_free_rate={risk_free_rate})")
    
    def run_annual_rebalancing(
        self,
        start_year: int,
        end_year: int,
        strategy: str = 'offensive',
        top_n: int = 10
    ) -> Dict:
        """
        执行年度调仓策略回测
        
        Args:
            start_year: 起始年份
            end_year: 结束年份
            strategy: 策略类型（'offensive'或'defensive'）
            top_n: 每年选择的股票数量
            
        Returns:
            回测结果字典，包含组合收益和绩效指标
        """
        try:
            # 验证策略类型
            if strategy not in ['offensive', 'defensive']:
                logger.warning(f"Invalid strategy: {strategy}, using 'offensive'")
                strategy = 'offensive'
            
            logger.info(f"Starting annual rebalancing backtest: {start_year}-{end_year}, strategy={strategy}")
            
            # 逐年执行调仓
            portfolio_returns = []
            yearly_holdings = []
            
            for year in range(start_year, end_year + 1):
                # 1. 获取该年的综合评分
                scores_df = self.data_loader.load_composite_scores(year=year)
                
                if scores_df.empty:
                    logger.warning(f"No composite scores for year {year}, skipping")
                    continue
                
                # 2. 选股
                selected_stocks = self._select_top_stocks(
                    scores_df, 
                    strategy=strategy, 
                    top_n=top_n
                )
                
                if selected_stocks.empty:
                    logger.warning(f"No stocks selected for year {year}")
                    continue
                
                # 3. 模拟持仓收益（简化版，实际应接入真实行情）
                year_return = self._simulate_year_return(selected_stocks, year)
                
                portfolio_returns.append({
                    'year': year,
                    'return': year_return,
                    'holdings_count': len(selected_stocks)
                })
                
                yearly_holdings.append(selected_stocks)
            
            # 4. 计算绩效指标
            performance_metrics = self._calculate_performance_metrics(portfolio_returns)
            
            result = {
                'portfolio_returns': portfolio_returns,
                'performance_metrics': performance_metrics,
                'yearly_holdings': yearly_holdings
            }
            
            logger.info(f"Backtest completed: {len(portfolio_returns)} years")
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            return {
                'portfolio_returns': [],
                'performance_metrics': self._default_metrics(),
                'yearly_holdings': []
            }
    
    def _select_top_stocks(
        self, 
        scores_df: pd.DataFrame, 
        strategy: str, 
        top_n: int
    ) -> pd.DataFrame:
        """
        选择得分最高的股票
        
        Args:
            scores_df: 综合评分DataFrame
            strategy: 策略类型
            top_n: 选择数量
            
        Returns:
            选中的股票DataFrame
        """
        # 排除红色风险股票（如果该列存在）
        if 'composite_risk_level' in scores_df.columns:
            filtered_df = scores_df[scores_df['composite_risk_level'] != 'red'].copy()
        else:
            filtered_df = scores_df.copy()
            logger.warning("composite_risk_level column not found, skipping risk filter")
        
        if filtered_df.empty:
            logger.warning("All stocks have red risk level or no data")
            return pd.DataFrame()
        
        # 根据策略排序
        score_column = f'{strategy}_score'
        if score_column not in filtered_df.columns:
            logger.error(f"Score column {score_column} not found")
            return pd.DataFrame()
        
        # 按得分降序排列，选择top_n
        selected = filtered_df.nlargest(top_n, score_column)
        
        logger.info(f"Selected {len(selected)} stocks using {strategy} strategy")
        return selected
    
    def _simulate_year_return(self, selected_stocks: pd.DataFrame, year: int) -> float:
        """
        模拟年度收益（简化版）
        
        注意：实际实现应该接入真实行情数据计算收益
        这里使用简化逻辑用于测试
        
        Args:
            selected_stocks: 选中的股票
            year: 年份
            
        Returns:
            组合收益率
        """
        # TODO: 接入真实行情数据
        # 当前简化实现：基于平均得分估算收益
        if 'offensive_score' in selected_stocks.columns:
            avg_score = selected_stocks['offensive_score'].mean()
        elif 'defensive_score' in selected_stocks.columns:
            avg_score = selected_stocks['defensive_score'].mean()
        else:
            avg_score = 50
        
        # 简化的收益映射：得分越高，预期收益越高
        # 假设：80分对应15%收益，50分对应5%收益，20分对应-5%收益
        base_return = 0.05  # 基础收益5%
        score_factor = (avg_score - 50) / 100  # 得分因子
        
        simulated_return = base_return + score_factor * 0.2  # ±10%的波动
        
        return simulated_return
    
    def _calculate_performance_metrics(self, portfolio_returns: List[Dict]) -> Dict:
        """
        计算绩效指标
        
        Args:
            portfolio_returns: 年度收益列表
            
        Returns:
            绩效指标字典
        """
        if not portfolio_returns:
            return self._default_metrics()
        
        # 提取收益率序列
        returns = [item['return'] for item in portfolio_returns]
        returns_series = pd.Series(returns)
        
        # 总收益
        total_return = self._calculate_total_return(returns)
        
        # 年化收益
        years = len(returns)
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio(returns_series)
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown_from_returns(returns_series)
        
        # 胜率
        win_rate = (returns_series > 0).sum() / len(returns_series) if len(returns_series) > 0 else 0
        
        # 波动率
        volatility = returns_series.std() if len(returns_series) > 1 else 0
        
        metrics = {
            'total_return': round(total_return, 4),
            'annualized_return': round(annualized_return, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 4),
            'win_rate': round(win_rate, 4),
            'volatility': round(volatility, 4),
            'years_backtested': years
        }
        
        return metrics
    
    def _calculate_total_return(self, returns: List[float]) -> float:
        """
        计算总收益（复利）
        
        Args:
            returns: 年度收益率列表
            
        Returns:
            总收益率
        """
        cumulative = 1.0
        for r in returns:
            cumulative *= (1 + r)
        
        return cumulative - 1
    
    def _calculate_portfolio_return(self, holdings: pd.DataFrame) -> float:
        """
        计算组合收益率
        
        Args:
            holdings: 持仓DataFrame，包含weight、entry_price、exit_price列
            
        Returns:
            组合收益率
        """
        if holdings.empty:
            return 0.0
        
        # 计算每只股票的收益率
        holdings['stock_return'] = (holdings['exit_price'] - holdings['entry_price']) / holdings['entry_price']
        
        # 加权平均
        portfolio_return = (holdings['weight'] * holdings['stock_return']).sum()
        
        return portfolio_return
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = None) -> float:
        """
        计算夏普比率
        
        公式：(年化收益 - 无风险利率) / 年化波动率
        
        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率
            
        Returns:
            夏普比率
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
        
        if len(returns) < 2 or returns.std() == 0:
            return 0.0
        
        # 年化收益
        annual_return = returns.mean() * len(returns)
        
        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(len(returns))
        
        if annual_volatility == 0:
            return 0.0
        
        sharpe = (annual_return - risk_free_rate) / annual_volatility
        
        return sharpe
    
    def _calculate_max_drawdown_from_returns(self, returns: pd.Series) -> float:
        """
        从收益率序列计算最大回撤
        
        Args:
            returns: 收益率序列
            
        Returns:
            最大回撤（正数）
        """
        if len(returns) == 0:
            return 0.0
        
        # 计算累计净值
        net_values = (1 + returns).cumprod()
        
        return self._calculate_max_drawdown(net_values)
    
    def _calculate_max_drawdown(self, net_values: pd.Series) -> float:
        """
        计算最大回撤
        
        公式：max((peak - trough) / peak)
        
        Args:
            net_values: 净值序列
            
        Returns:
            最大回撤（正数）
        """
        if len(net_values) == 0:
            return 0.0
        
        # 计算累积最大值
        cumulative_max = net_values.cummax()
        
        # 计算回撤
        drawdowns = (cumulative_max - net_values) / cumulative_max
        
        # 最大回撤
        max_dd = drawdowns.max()
        
        return max_dd
    
    def _convert_to_qlib_format(self, scores_df: pd.DataFrame) -> pd.DataFrame:
        """
        将因子数据转换为Qlib格式
        
        Qlib要求的格式：
        - instrument: 股票代码
        - datetime: 日期
        - factor_name: 因子值
        
        Args:
            scores_df: 综合评分DataFrame
            
        Returns:
            Qlib格式的DataFrame
        """
        if scores_df.empty:
            return pd.DataFrame()
        
        # 简化转换：添加datetime列
        qlib_df = scores_df.copy()
        qlib_df['datetime'] = pd.to_datetime(qlib_df['report_year'].astype(str) + '-01-01')
        qlib_df['instrument'] = qlib_df['stock_code']
        
        logger.info(f"Converted {len(qlib_df)} records to Qlib format")
        return qlib_df
    
    def _default_metrics(self) -> Dict:
        """返回默认的绩效指标（空结果时使用）"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'volatility': 0.0,
            'years_backtested': 0
        }
