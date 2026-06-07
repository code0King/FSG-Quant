"""
因子合成器

整合L1/L2/L3层因子，执行：
1. 施密特正交化（消除多重共线性）
2. 进攻型打分卡计算
3. 防御型打分卡计算
4. 综合风险等级评定

使用示例：
    >>> from data_pipeline.data_loader import DataLoader
    >>> 
    >>> loader = DataLoader()
    >>> synthesizer = FactorSynthesizer(loader)
    >>> result = synthesizer.calculate_all(2023)
    >>> print(result[['stock_code', 'offensive_score', 'defensive_score', 'composite_risk_level']])
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class FactorSynthesizer:
    """
    因子合成器
    
    整合多层因子，生成综合评分和风险等级。
    
    Attributes:
        data_loader: 数据加载器实例
        weights: 打分卡权重配置
    """
    
    def __init__(self, data_loader, config_path: str = 'config/factor_weights.yaml'):
        """
        初始化因子合成器
        
        Args:
            data_loader: DataLoader实例
            config_path: 权重配置文件路径
        """
        self.data_loader = data_loader
        self.weights = self._load_weights(config_path)
        
        logger.info("FactorSynthesizer initialized")
    
    def _load_weights(self, config_path: str) -> Dict:
        """
        加载打分卡权重配置
        
        Args:
            config_path: YAML配置文件路径
            
        Returns:
            权重字典
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._default_weights()
            
            with open(config_file, 'r', encoding='utf-8') as f:
                weights = yaml.safe_load(f)
            
            logger.info(f"Weights loaded from {config_path}")
            return weights
            
        except Exception as e:
            logger.error(f"Failed to load weights: {str(e)}, using defaults")
            return self._default_weights()
    
    def _default_weights(self) -> Dict:
        """返回默认权重配置"""
        return {
            'offensive': {
                'l2_fulfillment': 0.30,
                'l1_revenue_growth': 0.25,
                'l1_profit_quality': 0.20,
                'l3_governance': 0.15,
                'l2_sentiment': 0.10
            },
            'defensive': {
                'l3_governance': 0.35,
                'l1_cash_quality': 0.30,
                'l1_asset_health': 0.20,
                'l2_consistency': 0.10,
                'l1_stability': 0.05
            }
        }
    
    def calculate_all(self, year: int) -> pd.DataFrame:
        """
        计算所有股票的综合评分
        
        Args:
            year: 年份
            
        Returns:
            DataFrame包含所有股票的综合评分和风险等级
        """
        try:
            # 1. 加载各层因子数据
            l1_data = self.data_loader.load_factors(factor_type='L1', year=year)
            l2_data = self.data_loader.load_factors(factor_type='L2', year=year)
            l3_data = self.data_loader.load_factors(factor_type='L3', year=year)
            
            if l1_data.empty or l2_data.empty or l3_data.empty:
                logger.warning(f"Incomplete factor data for year {year}")
                return pd.DataFrame()
            
            # 2. 合并因子数据
            merged_data = self._merge_factor_data(l1_data, l2_data, l3_data)
            
            if merged_data.empty:
                return pd.DataFrame()
            
            # 3. 对每个股票计算评分
            results = []
            for _, row in merged_data.iterrows():
                stock_result = self._calculate_stock_scores(row)
                results.append(stock_result)
            
            result_df = pd.DataFrame(results)
            
            logger.info(f"Calculated scores for {len(result_df)} stocks in {year}")
            return result_df
            
        except Exception as e:
            logger.error(f"Failed to calculate all scores for year {year}: {str(e)}")
            return pd.DataFrame()
    
    def _merge_factor_data(self, l1_data: pd.DataFrame, l2_data: pd.DataFrame, 
                          l3_data: pd.DataFrame) -> pd.DataFrame:
        """
        合并L1/L2/L3层因子数据
        
        Args:
            l1_data: L1因子数据
            l2_data: L2因子数据
            l3_data: L3因子数据
            
        Returns:
            合并后的DataFrame
        """
        try:
            # 以L1为基础，左连接L2和L3
            merged = l1_data.merge(l2_data, on=['stock_code', 'report_year'], how='left')
            merged = merged.merge(l3_data, on=['stock_code', 'report_year'], how='left')
            
            return merged
            
        except Exception as e:
            logger.error(f"Failed to merge factor data: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_stock_scores(self, stock_data: pd.Series) -> Dict:
        """
        计算单只股票的评分
        
        Args:
            stock_data: 单只股票的所有因子数据
            
        Returns:
            评分结果字典
        """
        stock_code = stock_data['stock_code']
        year = stock_data['report_year']
        
        # 提取各类因子
        factors = self._extract_factors(stock_data)
        
        # 计算进攻型评分
        offensive_score = self._calculate_offensive_score(factors)
        
        # 计算防御型评分
        defensive_score = self._calculate_defensive_score(factors)
        
        # 获取治理风险等级
        governance_level = stock_data.get('governance_risk_level', 'yellow')
        
        # 评定综合风险等级
        risk_level = self._assess_composite_risk(
            offensive_score=offensive_score,
            defensive_score=defensive_score,
            governance_level=governance_level
        )
        
        return {
            'stock_code': stock_code,
            'report_year': year,
            'offensive_score': round(offensive_score, 2),
            'defensive_score': round(defensive_score, 2),
            'composite_risk_level': risk_level
        }
    
    def _extract_factors(self, stock_data: pd.Series) -> Dict:
        """
        从原始数据中提取因子值
        
        Args:
            stock_data: 原始因子数据
            
        Returns:
            标准化后的因子字典
        """
        factors = {}
        
        # L1因子
        factors['l1_revenue_growth'] = (stock_data.get('revenue_growth') or 0) * 100  # 转为百分比
        factors['l1_profit_quality'] = stock_data.get('profit_quality_score') or 50
        factors['l1_cash_quality'] = (stock_data.get('cash_flow_coverage') or 1.0) * 50  # 映射到0-100
        factors['l1_asset_health'] = stock_data.get('asset_health_score') or 50
        factors['l1_stability'] = (stock_data.get('roe') or 0.1) * 500  # ROE映射

        # L2因子
        factors['l2_fulfillment'] = stock_data.get('revenue_fulfillment_rate') or 100
        factors['l2_sentiment'] = ((stock_data.get('management_sentiment') or 0) + 1) * 50  # -1~1映射到0-100
        factors['l2_consistency'] = stock_data.get('strategy_execution_score') or 50
        
        # L3因子（治理评分，从风险等级转换）
        governance_level = stock_data.get('governance_risk_level', 'yellow')
        governance_score_map = {
            'green': 90,
            'yellow': 70,
            'orange': 50,
            'red': 30
        }
        factors['l3_governance'] = governance_score_map.get(governance_level, 50)
        
        return factors
    
    def _calculate_offensive_score(self, factors: Dict) -> float:
        """
        计算进攻型打分卡评分
        
        公式：Σ(因子值 × 权重)
        
        Args:
            factors: 因子字典
            
        Returns:
            进攻型评分（0-100）
        """
        weights = self.weights.get('offensive', {})
        
        score = 0.0
        for factor_name, weight in weights.items():
            factor_value = factors.get(factor_name, 50)  # 默认值50
            # 确保因子值在0-100范围内
            normalized_value = max(0, min(100, factor_value))
            score += normalized_value * weight
        
        return max(0, min(100, score))
    
    def _calculate_defensive_score(self, factors: Dict) -> float:
        """
        计算防御型打分卡评分
        
        公式：Σ(因子值 × 权重)
        
        Args:
            factors: 因子字典
            
        Returns:
            防御型评分（0-100）
        """
        weights = self.weights.get('defensive', {})
        
        score = 0.0
        for factor_name, weight in weights.items():
            factor_value = factors.get(factor_name, 50)  # 默认值50
            # 确保因子值在0-100范围内
            normalized_value = max(0, min(100, factor_value))
            score += normalized_value * weight
        
        return max(0, min(100, score))
    
    def _assess_composite_risk(self, offensive_score: float, defensive_score: float,
                              governance_level: str) -> str:
        """
        评定综合风险等级
        
        规则：
        1. 如果治理等级为red → 直接red
        2. 否则根据平均评分判定：
           - 平均分 >= 75 → green
           - 平均分 >= 60 → yellow
           - 平均分 >= 45 → orange
           - 平均分 < 45 → red
        
        Args:
            offensive_score: 进攻型评分
            defensive_score: 防御型评分
            governance_level: 治理风险等级
            
        Returns:
            综合风险等级
        """
        # 规则1：治理红色直接触发
        if governance_level == 'red':
            return 'red'
        
        # 规则2：基于平均评分
        avg_score = (offensive_score + defensive_score) / 2
        
        if avg_score >= 75:
            return 'green'
        elif avg_score >= 60:
            return 'yellow'
        elif avg_score >= 45:
            return 'orange'
        else:
            return 'red'
    
    def _schmidt_orthogonalization(self, vectors: List[np.ndarray]) -> List[np.ndarray]:
        """
        施密特正交化
        
        将一组线性无关的向量转换为正交向量组。
        
        Args:
            vectors: 向量列表，每个向量是一维numpy数组
            
        Returns:
            正交化后的向量列表
            
        Example:
            >>> v1 = np.array([1.0, 2.0, 3.0])
            >>> v2 = np.array([2.0, 3.0, 4.0])
            >>> orthogonal = _schmidt_orthogonalization([v1, v2])
            >>> np.dot(orthogonal[0], orthogonal[1])  # 接近0
        """
        if not vectors:
            return []
        
        orthogonal_vectors = []
        
        for i, v in enumerate(vectors):
            # 从当前向量开始
            u = v.copy().astype(float)
            
            # 减去在之前所有正交向量上的投影
            for j in range(i):
                proj_coefficient = np.dot(u, orthogonal_vectors[j]) / np.dot(orthogonal_vectors[j], orthogonal_vectors[j])
                u = u - proj_coefficient * orthogonal_vectors[j]
            
            # 如果向量不为零，添加到结果中
            norm = np.linalg.norm(u)
            if norm > 1e-10:  # 避免数值误差
                orthogonal_vectors.append(u)
            else:
                logger.warning(f"Vector {i} became zero after orthogonalization")
                orthogonal_vectors.append(np.zeros_like(v))
        
        return orthogonal_vectors
    
    def orthogonalize_factors(self, factor_matrix: np.ndarray) -> np.ndarray:
        """
        对因子矩阵进行正交化处理
        
        Args:
            factor_matrix: 因子矩阵，形状为(n_samples, n_factors)
            
        Returns:
            正交化后的因子矩阵
        """
        if factor_matrix.size == 0:
            return factor_matrix
        
        # 转置使得每列是一个因子向量
        vectors = [factor_matrix[:, i] for i in range(factor_matrix.shape[1])]
        
        # 执行施密特正交化
        orthogonal_vectors = self._schmidt_orthogonalization(vectors)
        
        # 转换回矩阵形式
        if orthogonal_vectors:
            orthogonal_matrix = np.column_stack(orthogonal_vectors)
            return orthogonal_matrix
        else:
            return factor_matrix
