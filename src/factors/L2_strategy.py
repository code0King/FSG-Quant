"""
L2战略执行层因子计算器

整合承诺抽取和情绪分析，计算战略执行相关因子：
1. 营收承诺兑现率
2. 利润承诺兑现率
3. 管理层情绪得分
4. 战略执行综合评分

使用示例：
    >>> from data_pipeline.data_loader import DataLoader
    >>> from nlp.commitment_parser import CommitmentParser
    >>> from nlp.finbert_analyzer import FinBERTAnalyzer
    >>> 
    >>> loader = DataLoader()
    >>> parser = CommitmentParser()
    >>> analyzer = FinBERTAnalyzer()
    >>> 
    >>> calculator = L2StrategyFactor(loader, parser, analyzer)
    >>> result = calculator.calculate_all('000001.SZ', 2023)
    >>> print(result['strategy_execution_score'])
"""
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class L2StrategyFactor:
    """
    L2战略执行层因子计算器
    
    基于MD&A文本分析和财务数据对比，评估公司战略执行情况。
    
    Attributes:
        data_loader: 数据加载器实例
        commitment_parser: 承诺抽取器实例
        finbert_analyzer: FinBERT情绪分析器实例
    """
    
    def __init__(self, data_loader, commitment_parser, finbert_analyzer):
        """
        初始化L2因子计算器
        
        Args:
            data_loader: DataLoader实例，用于加载财务数据
            commitment_parser: CommitmentParser实例，用于抽取承诺
            finbert_analyzer: FinBERTAnalyzer实例，用于情绪分析
        """
        self.data_loader = data_loader
        self.commitment_parser = commitment_parser
        self.finbert_analyzer = finbert_analyzer
        
        logger.info("L2StrategyFactor initialized")
    
    def calculate_all(self, stock_code: str, year: int) -> Optional[Dict]:
        """
        计算L2层所有因子
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            dict包含所有L2因子，失败返回None
            
        Example:
            >>> result = calculator.calculate_all('000001.SZ', 2023)
            >>> print(result.keys())
            dict_keys(['revenue_fulfillment_rate', 'profit_fulfillment_rate', ...])
        """
        try:
            # 1. 获取当年和上年财务数据
            current_data = self._get_financial_data(stock_code, year)
            last_year_data = self._get_financial_data(stock_code, year - 1)
            
            if not current_data:
                logger.warning(f"No financial data for {stock_code} in {year}")
                return None
            
            # 2. 获取MD&A文本（这里简化处理，实际应从数据库或文件读取）
            mda_text = self._get_mda_text(stock_code, year)
            
            # 3. 抽取战略承诺
            commitments = self.commitment_parser.extract_commitments(mda_text)
            
            # 4. 计算承诺兑现率
            revenue_fulfillment = None
            profit_fulfillment = None
            
            if commitments.get('has_explicit') and last_year_data:
                # 营收兑现率
                if commitments.get('revenue_growth_target'):
                    revenue_fulfillment = self._calculate_revenue_fulfillment_rate(
                        last_year_data, current_data, commitments['revenue_growth_target']
                    )
                
                # 利润兑现率
                if commitments.get('profit_growth_target'):
                    profit_fulfillment = self._calculate_profit_fulfillment_rate(
                        last_year_data, current_data, commitments['profit_growth_target']
                    )
            
            # 5. 计算管理层情绪得分
            management_sentiment = self._calculate_management_sentiment(mda_text)
            
            # 6. 计算战略执行综合评分
            # 如果有兑现率数据，使用兑现率和情绪；否则仅使用情绪
            if revenue_fulfillment is not None:
                avg_fulfillment = (revenue_fulfillment + (profit_fulfillment or revenue_fulfillment)) / 2
                strategy_score = self._composite_strategy_score(avg_fulfillment, management_sentiment)
            else:
                # 无承诺数据时，仅基于情绪评分（映射到0-100）
                strategy_score = max(0, min(100, (management_sentiment + 1) * 50))
            
            return {
                'revenue_fulfillment_rate': round(revenue_fulfillment, 2) if revenue_fulfillment else None,
                'profit_fulfillment_rate': round(profit_fulfillment, 2) if profit_fulfillment else None,
                'management_sentiment': round(management_sentiment, 4),
                'strategy_execution_score': round(strategy_score, 2),
                'has_explicit_commitment': commitments.get('has_explicit', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate L2 factors for {stock_code} {year}: {str(e)}")
            return None
    
    def _get_financial_data(self, stock_code: str, year: int) -> Optional[Dict]:
        """
        获取指定年份的财务数据
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            财务数据dict，包含revenue、net_profit等字段
        """
        try:
            df = self.data_loader.load_financial(stock_code=stock_code, year=year)
            
            if df is None or df.empty:
                return None
            
            # 转换为字典（取第一行）
            data_dict = df.iloc[0].to_dict()
            return data_dict
            
        except Exception as e:
            logger.error(f"Failed to load financial data for {stock_code} {year}: {str(e)}")
            return None
    
    def _get_mda_text(self, stock_code: str, year: int) -> str:
        """
        获取MD&A文本，优先从SQLite读取，再从PDF解析，最后fallback到默认文本。

        Args:
            stock_code: 股票代码
            year: 年份

        Returns:
            MD&A文本内容
        """
        # 1. 从SQLite mda_text表读取
        try:
            import sqlite3
            db_path = self.data_loader.db_path if hasattr(self.data_loader, 'db_path') else None
            if db_path and Path(db_path).exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mda_text FROM mda_text WHERE stock_code=? AND report_year=?",
                    (stock_code, year)
                )
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    logger.debug(f"Loaded MD&A from DB: {stock_code} {year} ({len(row[0])} chars)")
                    return row[0]
        except Exception as e:
            logger.debug(f"DB fallback for MD&A: {e}")

        # 2. 直接从PDF解析
        try:
            from data_pipeline.pdf_parser import AnnualReportParser
            pdf_path = Path("data/raw/annual_reports") / stock_code / f"{year}.pdf"
            if pdf_path.exists():
                parser = AnnualReportParser()
                result = parser.parse(str(pdf_path))
                if result.get('mda_text'):
                    return result['mda_text']
        except Exception as e:
            logger.debug(f"PDF fallback for MD&A: {e}")

        # 3. 默认文本
        return "公司业绩良好，未来发展可期。我们将继续加大研发投入，提升核心竞争力。"
    
    def _calculate_revenue_fulfillment_rate(
        self, 
        last_year_data: Dict, 
        current_year_data: Dict, 
        target_growth_rate: float
    ) -> float:
        """
        计算营收承诺兑现率
        
        公式：实际增长率 / 承诺增长率 * 100%
        
        Args:
            last_year_data: 上年财务数据
            current_year_data: 本年财务数据
            target_growth_rate: 承诺的增长率（百分比）
            
        Returns:
            兑现率（百分比），可能超过100%表示超额完成
            
        Example:
            >>> # 承诺增长20%，实际从800增长到1000（增长25%）
            >>> rate = _calculate_revenue_fulfillment_rate(
            ...     {'revenue': 800}, {'revenue': 1000}, 20.0
            ... )
            >>> print(rate)  # 125.0
        """
        try:
            last_revenue = last_year_data.get('revenue', 0)
            current_revenue = current_year_data.get('revenue', 0)
            
            # 防止除零
            if last_revenue == 0:
                logger.warning("Last year revenue is zero")
                return 0.0
            
            # 计算实际增长率
            actual_growth_rate = ((current_revenue - last_revenue) / last_revenue) * 100
            
            # 防止承诺增长率为0
            if target_growth_rate == 0:
                return 100.0 if actual_growth_rate >= 0 else 0.0
            
            # 计算兑现率
            fulfillment_rate = (actual_growth_rate / target_growth_rate) * 100
            
            # 确保非负
            return max(0.0, fulfillment_rate)
            
        except Exception as e:
            logger.error(f"Failed to calculate revenue fulfillment rate: {str(e)}")
            return 0.0
    
    def _calculate_profit_fulfillment_rate(
        self, 
        last_year_data: Dict, 
        current_year_data: Dict, 
        target_growth_rate: float
    ) -> float:
        """
        计算利润承诺兑现率
        
        公式：实际增长率 / 承诺增长率 * 100%
        
        Args:
            last_year_data: 上年财务数据
            current_year_data: 本年财务数据
            target_growth_rate: 承诺的增长率（百分比）
            
        Returns:
            兑现率（百分比）
        """
        try:
            last_profit = last_year_data.get('net_profit', 0)
            current_profit = current_year_data.get('net_profit', 0)
            
            # 防止除零
            if last_profit == 0:
                logger.warning("Last year profit is zero")
                return 0.0
            
            # 计算实际增长率
            actual_growth_rate = ((current_profit - last_profit) / last_profit) * 100
            
            # 防止承诺增长率为0
            if target_growth_rate == 0:
                return 100.0 if actual_growth_rate >= 0 else 0.0
            
            # 计算兑现率
            fulfillment_rate = (actual_growth_rate / target_growth_rate) * 100
            
            # 确保非负
            return max(0.0, fulfillment_rate)
            
        except Exception as e:
            logger.error(f"Failed to calculate profit fulfillment rate: {str(e)}")
            return 0.0
    
    def _calculate_management_sentiment(self, mda_text: str) -> float:
        """
        计算管理层情绪得分
        
        Args:
            mda_text: MD&A文本
            
        Returns:
            情绪得分（-1到1）
        """
        if not mda_text or not mda_text.strip():
            return 0.0
        
        try:
            result = self.finbert_analyzer.analyze_mda_section(mda_text)
            return result.get('overall_sentiment', 0.0)
            
        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {str(e)}")
            return 0.0
    
    def _composite_strategy_score(
        self, 
        avg_fulfillment_rate: float, 
        sentiment_score: float
    ) -> float:
        """
        计算战略执行综合评分
        
        加权组合兑现率和情绪得分：
        - 兑现率权重：70%
        - 情绪得分权重：30%
        
        Args:
            avg_fulfillment_rate: 平均兑现率（百分比，0-200+）
            sentiment_score: 情绪得分（-1到1）
            
        Returns:
            综合评分（0-100）
            
        Example:
            >>> score = _composite_strategy_score(120.0, 0.8)
            >>> print(score)  # 约85分
        """
        # 将兑现率映射到0-100（100%兑现率对应70分）
        fulfillment_score = min(100, avg_fulfillment_rate * 0.7)
        
        # 将情绪得分映射到0-100（-1到1映射到0-100）
        sentiment_mapped = (sentiment_score + 1) * 50
        
        # 加权组合
        final_score = (
            0.7 * fulfillment_score +
            0.3 * sentiment_mapped
        )
        
        # 确保在0-100范围内
        return max(0.0, min(100.0, final_score))
