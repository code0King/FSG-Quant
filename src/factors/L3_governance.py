"""
L3治理排雷层因子计算器

监控公司治理风险，包括：
1. 股权质押比例
2. 审计意见类型
3. 高管流失率
4. 综合风险等级评定（green/yellow/orange/red）

使用示例：
    >>> from data_pipeline.data_loader import DataLoader
    >>> 
    >>> loader = DataLoader()
    >>> calculator = L3GovernanceFactor(loader)
    >>> result = calculator.calculate_all('000001.SZ', 2023)
    >>> print(result['governance_risk_level'])  # 'green'
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class L3GovernanceFactor:
    """
    L3治理排雷层因子计算器
    
    基于公司治理数据，评估潜在风险和排雷信号。
    
    Attributes:
        data_loader: 数据加载器实例
    """
    
    # 风险阈值配置
    PLEDGE_THRESHOLDS = {
        'green': 20,      # <20% 绿色
        'yellow': 40,     # 20-40% 黄色
        'orange': 60,     # 40-60% 橙色
        'red': 60         # >60% 红色
    }
    
    TURNOVER_THRESHOLDS = {
        'green': 10,      # <10% 绿色
        'yellow': 20,     # 10-20% 黄色
        'orange': 30,     # 20-30% 橙色
        'red': 30         # >30% 红色
    }
    
    def __init__(self, data_loader):
        """
        初始化L3因子计算器
        
        Args:
            data_loader: DataLoader实例，用于加载治理数据
        """
        self.data_loader = data_loader
        
        logger.info("L3GovernanceFactor initialized")
    
    def calculate_all(self, stock_code: str, year: int) -> Optional[Dict]:
        """
        计算L3层所有因子
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            dict包含所有L3因子，失败返回None
            
        Example:
            >>> result = calculator.calculate_all('000001.SZ', 2023)
            >>> print(result.keys())
            dict_keys(['pledge_ratio', 'audit_opinion', ...])
        """
        try:
            # 1. 获取股权质押比例
            pledge_ratio = self._calculate_pledge_ratio(stock_code, year)
            
            # 2. 获取审计意见
            audit_opinion = self._get_audit_opinion(stock_code, year)
            is_non_standard = self._is_non_standard_audit(audit_opinion)
            
            # 3. 计算高管流失率
            executive_turnover = self._calculate_executive_turnover(stock_code, year)
            
            # 4. 评定治理风险等级
            risk_level = self._assess_governance_risk(
                pledge_ratio=pledge_ratio or 0,
                is_non_standard_audit=is_non_standard,
                executive_turnover=executive_turnover or 0
            )
            
            return {
                'pledge_ratio': round(pledge_ratio, 2) if pledge_ratio else None,
                'audit_opinion': audit_opinion,
                'is_non_standard_audit': is_non_standard,
                'executive_turnover': round(executive_turnover, 2) if executive_turnover else None,
                'governance_risk_level': risk_level
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate L3 factors for {stock_code} {year}: {str(e)}")
            return None
    
    def _calculate_pledge_ratio(self, stock_code: str, year: int) -> Optional[float]:
        """
        计算股权质押比例
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            质押比例（百分比，0-100），无数据返回None
            
        Example:
            >>> ratio = _calculate_pledge_ratio('000001.SZ', 2023)
            >>> print(ratio)  # 15.5
        """
        try:
            df = self.data_loader.load_governance(
                data_type='pledge',
                stock_code=stock_code,
                year=year
            )
            
            if df is None or df.empty:
                logger.debug(f"No pledge data for {stock_code} in {year}")
                return None
            
            # 获取质押比例
            ratio = df.iloc[0]['pledged_shares_ratio']
            return float(ratio)
            
        except Exception as e:
            logger.error(f"Failed to calculate pledge ratio for {stock_code} {year}: {str(e)}")
            return None
    
    def _get_audit_opinion(self, stock_code: str, year: int) -> str:
        """
        获取审计意见类型
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            审计意见文本，默认返回'未知'
        """
        try:
            df = self.data_loader.load_governance(
                data_type='audit',
                stock_code=stock_code,
                year=year
            )
            
            if df is None or df.empty:
                logger.debug(f"No audit data for {stock_code} in {year}")
                return '未知'
            
            opinion = df.iloc[0]['audit_opinion']
            return str(opinion)
            
        except Exception as e:
            logger.error(f"Failed to get audit opinion for {stock_code} {year}: {str(e)}")
            return '未知'
    
    def _is_non_standard_audit(self, audit_opinion: str) -> bool:
        """
        判断是否为非标审计意见
        
        非标意见包括：
        - 保留意见
        - 否定意见
        - 无法表示意见
        - 带强调事项段的无保留意见
        
        Args:
            audit_opinion: 审计意见文本
            
        Returns:
            True表示非标意见，False表示标准意见
        """
        if not audit_opinion or audit_opinion == '未知':
            return False
        
        # 标准意见关键词
        standard_keywords = ['标准无保留意见']
        
        # 检查是否为标准意见
        for keyword in standard_keywords:
            if keyword in audit_opinion:
                return False
        
        # 其他情况视为非标意见
        non_standard_keywords = [
            '保留意见',
            '否定意见',
            '无法表示意见',
            '强调事项'
        ]
        
        for keyword in non_standard_keywords:
            if keyword in audit_opinion:
                return True
        
        # 如果既不是标准也不是明确的非标，保守起见返回False
        return False
    
    def _calculate_executive_turnover(self, stock_code: str, year: int) -> Optional[float]:
        """
        计算高管流失率
        
        公式：流失人数 / 年初人数 * 100%
        
        Args:
            stock_code: 股票代码
            year: 年份
            
        Returns:
            流失率（百分比，0-100），无数据返回None
            
        Example:
            >>> rate = _calculate_executive_turnover('000001.SZ', 2023)
            >>> print(rate)  # 10.0 (年初10人，流失1人)
        """
        try:
            df = self.data_loader.load_governance(
                data_type='executive',
                stock_code=stock_code,
                year=year
            )
            
            if df is None or df.empty:
                logger.debug(f"No executive data for {stock_code} in {year}")
                return None
            
            # 获取数据（可能有多条记录，取第一条或求和）
            row = df.iloc[0]
            start_count = float(row.get('executive_count_start', 0))
            departed = float(row.get('departed_executives', 0))
            
            # 防止除零
            if start_count == 0:
                logger.warning(f"Executive count start is zero for {stock_code} {year}")
                return 0.0
            
            # 计算流失率
            turnover_rate = (departed / start_count) * 100
            
            # 确保在合理范围内
            return max(0.0, min(100.0, turnover_rate))
            
        except Exception as e:
            logger.error(f"Failed to calculate executive turnover for {stock_code} {year}: {str(e)}")
            return None
    
    def _assess_governance_risk(
        self,
        pledge_ratio: float,
        is_non_standard_audit: bool,
        executive_turnover: float
    ) -> str:
        """
        评定治理风险等级
        
        评级逻辑：
        1. 如果有非标审计意见 → 直接红色
        2. 否则根据质押率和流失率综合评定
           - 任一指标达到红色阈值 → 红色
           - 任一指标达到橙色阈值 → 橙色
           - 任一指标达到黄色阈值 → 黄色
           - 否则 → 绿色
        
        Args:
            pledge_ratio: 股权质押比例（0-100）
            is_non_standard_audit: 是否非标审计意见
            executive_turnover: 高管流失率（0-100）
            
        Returns:
            风险等级：'green'/'yellow'/'orange'/'red'
            
        Example:
            >>> level = _assess_governance_risk(15.0, False, 5.0)
            >>> print(level)  # 'green'
        """
        # 规则1：非标审计意见直接红色
        if is_non_standard_audit:
            logger.warning("Non-standard audit opinion detected → RED risk")
            return 'red'
        
        # 规则2：检查各指标的严重程度
        pledge_level = self._get_risk_level_by_threshold(
            pledge_ratio, self.PLEDGE_THRESHOLDS
        )
        turnover_level = self._get_risk_level_by_threshold(
            executive_turnover, self.TURNOVER_THRESHOLDS
        )
        
        # 取最严重的等级
        risk_levels = ['green', 'yellow', 'orange', 'red']
        max_level_idx = max(
            risk_levels.index(pledge_level),
            risk_levels.index(turnover_level)
        )
        
        final_level = risk_levels[max_level_idx]
        
        logger.debug(
            f"Risk assessment: pledge={pledge_level}, turnover={turnover_level} → {final_level}"
        )
        
        return final_level
    
    def _get_risk_level_by_threshold(self, value: float, thresholds: Dict[str, int]) -> str:
        """
        根据阈值判定风险等级
        
        Args:
            value: 待评估的数值
            thresholds: 阈值字典，格式 {'green': 20, 'yellow': 40, 'orange': 60, 'red': 60}
            
        Returns:
            风险等级字符串
        """
        if value < thresholds['green']:
            return 'green'
        elif value < thresholds['yellow']:
            return 'yellow'
        elif value < thresholds['orange']:
            return 'orange'
        else:
            return 'red'
