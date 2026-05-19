"""
战略承诺抽取器

从MD&A文本中抽取量化的战略承诺，使用正则表达式匹配。

支持的承诺类型：
1. 营收增长承诺（如"营收增长20%"）
2. 利润增长承诺（如"净利润增长15%"）
3. CAPEX/投资承诺（如"资本支出50亿元"）

使用示例：
    >>> parser = CommitmentParser()
    >>> result = parser.extract_commitments("预计营收增长20%")
    >>> print(result['revenue_growth_target'])  # 20.0
"""
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CommitmentParser:
    """
    战略承诺抽取器（方案A：正则表达式）
    
    从年报MD&A文本中抽取明确量化的承诺指标。
    
    Attributes:
        patterns: 正则表达式模式列表
    """
    
    # 正则表达式模式列表
    # 格式：(正则表达式, 目标类型)
    PATTERNS = [
        # 营收增长相关
        (r'营收.*?增长.*?(\d+\.?\d*)\s*%', 'revenue_growth'),
        (r'营业收入.*?增长.*?(\d+\.?\d*)\s*%', 'revenue_growth'),
        (r'收入.*?增长.*?(\d+\.?\d*)\s*%', 'revenue_growth'),
        
        # 利润增长相关
        (r'净利润.*?增长.*?(\d+\.?\d*)\s*%', 'profit_growth'),
        (r'利润.*?增长.*?(\d+\.?\d*)\s*%', 'profit_growth'),
        
        # CAPEX/投资相关
        (r'资本支出.*?(\d+\.?\d*)\s*亿元', 'capex'),
        (r'投资.*?(\d+\.?\d*)\s*亿元', 'capex'),
        (r'CAPEX.*?(\d+\.?\d*)\s*亿元', 'capex'),
    ]
    
    def __init__(self):
        """初始化承诺抽取器"""
        logger.info("CommitmentParser initialized")
    
    def extract_commitments(self, text: str) -> Dict[str, Optional[float]]:
        """
        从文本中抽取承诺指标
        
        Args:
            text: MD&A文本
            
        Returns:
            承诺字典，包含以下字段：
            - revenue_growth_target: 营收增速目标（float或None）
            - profit_growth_target: 利润增速目标（float或None）
            - capex_target: CAPEX目标（元，float或None）
            - has_explicit: 是否有明确承诺（bool）
            
        Example:
            >>> parser = CommitmentParser()
            >>> text = "预计营收增长20%，净利润增长15%"
            >>> result = parser.extract_commitments(text)
            >>> print(result['revenue_growth_target'])  # 20.0
            >>> print(result['profit_growth_target'])   # 15.0
        """
        result = {
            'revenue_growth_target': None,
            'profit_growth_target': None,
            'capex_target': None,
            'has_explicit': False
        }
        
        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided")
            return result
        
        # 遍历所有模式，查找匹配
        for pattern, target_type in self.PATTERNS:
            matches = re.findall(pattern, text)
            
            if matches:
                try:
                    # 取第一个匹配的数值
                    value = float(matches[0])
                    
                    # 根据目标类型设置相应的字段
                    if target_type == 'revenue_growth':
                        result['revenue_growth_target'] = value
                        result['has_explicit'] = True
                        logger.debug(f"Found revenue growth commitment: {value}%")
                        
                    elif target_type == 'profit_growth':
                        result['profit_growth_target'] = value
                        result['has_explicit'] = True
                        logger.debug(f"Found profit growth commitment: {value}%")
                        
                    elif target_type == 'capex':
                        # 转换为元（亿元 * 1e8）
                        result['capex_target'] = value * 1e8
                        result['has_explicit'] = True
                        logger.debug(f"Found CAPEX commitment: {value}亿元")
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse commitment value: {e}")
                    continue
        
        if result['has_explicit']:
            logger.info("Explicit commitments found")
        else:
            logger.debug("No explicit commitments found")
        
        return result
    
    def extract_from_sections(self, sections: list) -> Dict[str, Optional[float]]:
        """
        从多个章节文本中抽取承诺
        
        Args:
            sections: 章节文本列表
            
        Returns:
            承诺字典（同extract_commitments）
        """
        # 合并所有章节文本
        combined_text = " ".join(sections)
        return self.extract_commitments(combined_text)


# 便捷函数
def parse_commitments(text: str) -> Dict[str, Optional[float]]:
    """
    便捷函数：直接从文本抽取承诺
    
    Args:
        text: MD&A文本
        
    Returns:
        承诺字典
    """
    parser = CommitmentParser()
    return parser.extract_commitments(text)
