"""
L1业绩验证层因子计算器

基于财务报表数据计算盈利能力、盈利质量和资产健康度相关因子。

主要功能：
1. 计算ROE、ROA、ROIC等基础盈利指标
2. 行业差异化的毛利率分级评价
3. 盈利质量综合评分（0-100分）
4. 预警标记生成

使用示例：
    >>> calculator = L1PerformanceFactor(db_path, config_path)
    >>> result = calculator.calculate_all('000001.SZ', 2023)
    >>> print(result['profit_quality_score'])
"""
import pandas as pd
import sqlite3
from pathlib import Path
import logging
from typing import Optional, Dict, Tuple
import yaml
from scipy import stats

logger = logging.getLogger(__name__)


class L1PerformanceFactor:
    """
    L1业绩验证层因子计算器
    
    从SQLite数据库读取财务数据，计算7个核心因子：
    - ROE（净资产收益率）
    - ROA（总资产收益率）
    - ROIC（投入资本回报率）
    - 毛利率及分级评价
    - 扣非净利润占比
    - 现金流覆盖倍数
    - 盈利质量综合评分
    
    Attributes:
        db_path: SQLite数据库路径
        industry_config: 行业阈值配置字典
    """
    
    def __init__(self, db_path: str, industry_config_path: str):
        """
        初始化L1因子计算器
        
        Args:
            db_path: SQLite数据库文件路径
            industry_config_path: 行业阈值配置文件路径（YAML格式）
        """
        self.db_path = Path(db_path)
        self.industry_config = self._load_industry_config(industry_config_path)
        logger.info(f"L1PerformanceFactor initialized with DB: {db_path}")
    
    def _load_industry_config(self, config_path: str) -> dict:
        """
        加载行业阈值配置
        
        Args:
            config_path: YAML配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Industry config loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load industry config: {e}")
            # 返回默认配置
            return {
                'default_thresholds': {
                    'min_roe': 8,
                    'min_research_intensity': 2,
                    'max_goodwill_ratio': 20
                }
            }
    
    def calculate_all(self, stock_code: str, year: int) -> Optional[Dict]:
        """
        计算L1层所有因子
        
        Args:
            stock_code: 股票代码（如'000001.SZ'）
            year: 报告年度（如2023）
            
        Returns:
            因子字典，包含以下字段：
            - roe: ROE
            - roa: ROA
            - roic: ROIC
            - gross_margin: 毛利率
            - gross_margin_grade: 毛利率等级（高/中/低/极低）
            - gross_margin_score: 毛利率分数（0/30/60/100）
            - deducted_profit_ratio: 扣非净利润占比
            - cash_flow_coverage: 现金流覆盖倍数
            - profit_quality_score: 盈利质量综合评分（0-100）
            - warning_flags: 预警标记列表
            
        Example:
            >>> calculator = L1PerformanceFactor('data.sqlite', 'config.yaml')
            >>> result = calculator.calculate_all('000001.SZ', 2023)
            >>> print(f"ROE: {result['roe']:.2%}")
            >>> print(f"Quality Score: {result['profit_quality_score']}")
        """
        try:
            # Step 1: 获取财务数据
            financial = self._get_financial_data(stock_code, year)
            
            if financial is None or len(financial) == 0:
                logger.warning(f"No data for {stock_code} {year}")
                return None
            
            # 转换为字典
            fin_dict = financial.iloc[0].to_dict()
            
            # Step 2: 计算基础因子
            roe = self._calculate_roe(fin_dict)
            roa = self._calculate_roa(fin_dict)
            roic = self._calculate_roic(fin_dict)
            gross_margin = self._calculate_gross_margin(fin_dict)
            
            # Step 3: 毛利率分级（行业差异化）
            grade, score = self._evaluate_gross_margin(stock_code, year, gross_margin)
            
            # Step 4: 扣非净利润占比
            deducted_ratio = self._calculate_deducted_ratio(fin_dict)
            
            # Step 5: 现金流覆盖倍数
            cash_coverage = self._calculate_cash_coverage(fin_dict)
            
            # Step 6: 盈利质量综合评分
            profit_quality = self._composite_profit_quality(
                roe, roic, cash_coverage, deducted_ratio, score
            )
            
            # Step 7: 预警标记
            warnings = self._check_warnings(fin_dict, cash_coverage, deducted_ratio)
            
            return {
                'roe': round(roe, 4),
                'roa': round(roa, 4),
                'roic': round(roic, 4),
                'gross_margin': round(gross_margin, 4),
                'gross_margin_grade': grade,
                'gross_margin_score': score,
                'deducted_profit_ratio': round(deducted_ratio, 4),
                'cash_flow_coverage': round(cash_coverage, 4),
                'profit_quality_score': round(profit_quality, 2),
                'warning_flags': warnings
            }
            
        except Exception as e:
            logger.error(f"Error calculating L1 factors for {stock_code} {year}: {e}")
            return None
    
    def _get_financial_data(self, stock_code: str, year: int) -> Optional[pd.DataFrame]:
        """
        从SQLite获取财务数据
        
        Args:
            stock_code: 股票代码
            year: 报告年度
            
        Returns:
            DataFrame或None（如果数据不存在）
        """
        if not self.db_path.exists():
            logger.error(f"Database file not found: {self.db_path}")
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT * FROM financial_annual 
                WHERE stock_code = ? AND report_year = ?
            """
            df = pd.read_sql_query(query, conn, params=(stock_code, year))
            conn.close()
            
            if df.empty:
                return None
            
            return df
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return None
    
    def _calculate_roe(self, financial: dict) -> float:
        """
        计算ROE（净资产收益率）
        
        公式：ROE = 净利润 / 净资产
        
        Args:
            financial: 财务数据字典
            
        Returns:
            ROE值，如果分母为0则返回0
        """
        net_profit = financial.get('net_profit', 0)
        net_assets = financial.get('net_assets', 0)
        
        if net_assets == 0:
            return 0.0
        
        return net_profit / net_assets
    
    def _calculate_roa(self, financial: dict) -> float:
        """
        计算ROA（总资产收益率）
        
        公式：ROA = 净利润 / 总资产
        
        Args:
            financial: 财务数据字典
            
        Returns:
            ROA值，如果分母为0则返回0
        """
        net_profit = financial.get('net_profit', 0)
        total_assets = financial.get('total_assets', 0)
        
        if total_assets == 0:
            return 0.0
        
        return net_profit / total_assets
    
    def _calculate_roic(self, financial: dict) -> float:
        """
        计算ROIC（投入资本回报率）
        
        简化公式：ROIC = 净利润 / 净资产
        （完整公式需考虑有息负债和税盾效应）
        
        Args:
            financial: 财务数据字典
            
        Returns:
            ROIC值，如果分母为0则返回0
        """
        net_profit = financial.get('net_profit', 0)
        net_assets = financial.get('net_assets', 0)
        
        if net_assets == 0:
            return 0.0
        
        return net_profit / net_assets
    
    def _calculate_gross_margin(self, financial: dict) -> float:
        """
        计算毛利率
        
        公式：毛利率 = 毛利润 / 营业收入
        
        Args:
            financial: 财务数据字典
            
        Returns:
            毛利率值，如果分母为0则返回0
        """
        gross_profit = financial.get('gross_profit', 0)
        revenue = financial.get('revenue', 0)
        
        if revenue == 0:
            return 0.0
        
        return gross_profit / revenue
    
    def _evaluate_gross_margin(self, stock_code: str, year: int, margin: float) -> Tuple[str, int]:
        """
        行业差异化的毛利率分级评价
        
        根据公司在行业内的分位数评定等级：
        - 前25%：高（100分）
        - 25%-50%：中（60分）
        - 50%-75%：低（30分）
        - 后25%：极低（0分）
        
        Args:
            stock_code: 股票代码
            year: 报告年度
            margin: 毛利率值
            
        Returns:
            (等级, 分数) 元组
        """
        # 获取公司所属行业
        industry = self._get_industry(stock_code)
        
        # 获取同行业所有公司的毛利率
        all_margins = self._get_industry_margins(industry, year)
        
        if not all_margins or len(all_margins) < 3:
            # 数据不足，使用默认中等评级
            logger.warning(f"Insufficient industry data for {industry}, using default grading")
            return "中", 60
        
        # 计算分位数
        percentile = stats.percentileofscore(all_margins, margin)
        
        if percentile >= 75:
            return "高", 100
        elif percentile >= 50:
            return "中", 60
        elif percentile >= 25:
            return "低", 30
        else:
            return "极低", 0
    
    def _get_industry(self, stock_code: str) -> str:
        """
        获取公司所属行业
        
        Args:
            stock_code: 股票代码
            
        Returns:
            申万一级行业名称，未找到返回"未知"
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT industry_sw_level1 FROM companies WHERE stock_code = ?"
            cursor = conn.execute(query, (stock_code,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else "未知"
            
        except sqlite3.Error as e:
            logger.error(f"Error getting industry: {e}")
            return "未知"
    
    def _get_industry_margins(self, industry: str, year: int) -> list:
        """
        获取同行业所有公司的毛利率列表
        
        Args:
            industry: 行业名称
            year: 报告年度
            
        Returns:
            毛利率列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT f.gross_margin 
                FROM financial_annual f
                JOIN companies c ON f.stock_code = c.stock_code
                WHERE c.industry_sw_level1 = ? AND f.report_year = ?
                AND f.gross_margin IS NOT NULL
            """
            df = pd.read_sql_query(query, conn, params=(industry, year))
            conn.close()
            
            return df['gross_margin'].tolist()
            
        except sqlite3.Error as e:
            logger.error(f"Error getting industry margins: {e}")
            return []
    
    def _calculate_deducted_ratio(self, financial: dict) -> float:
        """
        计算扣非净利润占比
        
        公式：扣非净利润占比 = 扣非净利润 / 净利润
        
        Args:
            financial: 财务数据字典
            
        Returns:
            扣非净利润占比，如果分母为0则返回0
        """
        net_profit = financial.get('net_profit', 0)
        deducted = financial.get('net_profit_deducted', 0)
        
        if net_profit == 0:
            return 0.0
        
        return deducted / net_profit
    
    def _calculate_cash_coverage(self, financial: dict) -> float:
        """
        计算现金流覆盖倍数
        
        公式：现金流覆盖倍数 = 经营现金流 / 净利润
        
        Args:
            financial: 财务数据字典
            
        Returns:
            现金流覆盖倍数，如果分母为0则返回0
        """
        net_profit = financial.get('net_profit', 0)
        cash_flow = financial.get('operating_cash_flow', 0)
        
        if net_profit == 0:
            return 0.0
        
        return cash_flow / net_profit
    
    def _composite_profit_quality(self, roe: float, roic: float, 
                                  cash_cov: float, deducted_ratio: float,
                                  margin_score: int) -> float:
        """
        计算盈利质量综合评分
        
        权重分配：
        - ROE: 25%
        - ROIC: 20%
        - 现金流覆盖倍数: 20%
        - 扣非净利润占比: 15%
        - 毛利率等级分: 20%
        
        Args:
            roe: ROE值
            roic: ROIC值
            cash_cov: 现金流覆盖倍数
            deducted_ratio: 扣非净利润占比
            margin_score: 毛利率等级分（0/30/60/100）
            
        Returns:
            综合评分（0-100）
        """
        # 简单线性映射到0-100范围
        # 假设ROE在0-0.3之间，映射到0-100
        roe_score = min(100, max(0, roe * 333))  # 0.3 → 100
        
        # ROIC同理
        roic_score = min(100, max(0, roic * 333))
        
        # 现金流覆盖倍数：假设在0-3之间
        cash_score = min(100, max(0, cash_cov * 33.3))
        
        # 扣非占比已经是0-1，直接乘以100
        deducted_score = deducted_ratio * 100
        
        # 加权求和
        score = (
            0.25 * roe_score +
            0.20 * roic_score +
            0.20 * cash_score +
            0.15 * deducted_score +
            0.20 * margin_score
        )
        
        # 确保在0-100范围内
        return max(0, min(100, score))
    
    def _check_warnings(self, financial: dict, cash_coverage: float, 
                       deducted_ratio: float) -> list:
        """
        检查预警项
        
        预警条件：
        1. 现金流覆盖倍数 < 0.8
        2. 扣非净利润占比 < 0.5
        3. 应收账款/营收 > 0.3
        
        Args:
            financial: 财务数据字典
            cash_coverage: 现金流覆盖倍数
            deducted_ratio: 扣非净利润占比
            
        Returns:
            预警标记列表
        """
        warnings = []
        
        # 现金流预警
        if cash_coverage < 0.8:
            warnings.append("现金流覆盖不足")
        
        # 扣非占比预警
        if deducted_ratio < 0.5:
            warnings.append("扣非净利润占比低")
        
        # 应收账款预警
        revenue = financial.get('revenue', 1)
        accounts_receivable = financial.get('accounts_receivable', 0)
        
        if revenue > 0 and accounts_receivable / revenue > 0.3:
            warnings.append("应收账款占比高")
        
        return warnings
