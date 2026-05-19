"""
FinBERT情绪分析器

使用开源中文版FinBERT模型进行金融文本情绪分析。

支持的模型：
- uer/finbert-cn (HuggingFace)

返回结果：
- sentiment_score: 情绪得分（-1到1，负为负面，正为正面）
- label: 情绪标签（positive/neutral/negative）
- confidence: 置信度（0到1）

使用示例：
    >>> analyzer = FinBERTAnalyzer()
    >>> result = analyzer.analyze_sentiment("公司业绩大幅增长")
    >>> print(result['sentiment_score'])  # 正值表示正面
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 尝试导入torch和transformers
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers库未安装，FinBERT功能将不可用")
    logger.warning("请运行: pip install transformers torch sentencepiece")
    TRANSFORMERS_AVAILABLE = False


class FinBERTAnalyzer:
    """
    FinBERT情绪分析器
    
    基于预训练的中文金融BERT模型，对MD&A等文本进行情绪分析。
    
    Attributes:
        model_name: 模型名称或路径
        tokenizer: 分词器
        model: 分类模型
        device: 计算设备（cpu/cuda）
        max_length: 最大序列长度
    """
    
    # FinBERT-CN模型的标签映射
    LABEL_MAP = {
        0: 'negative',
        1: 'neutral', 
        2: 'positive'
    }
    
    def __init__(self, model_name: str = "uer/finbert-cn", max_length: int = 512):
        """
        初始化FinBERT分析器
        
        Args:
            model_name: HuggingFace模型名称或本地路径
            max_length: 最大序列长度（默认512）
        
        Raises:
            ImportError: 如果transformers库未安装
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers库未安装。请运行: pip install transformers torch sentencepiece"
            )
        
        self.model_name = model_name
        self.max_length = max_length
        
        logger.info(f"正在加载FinBERT模型: {model_name}")
        
        try:
            # 确定设备
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"使用设备: {self.device}")
            
            # 加载tokenizer和模型
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # 设置模型为评估模式并移动到设备
            self.model.eval()
            self.model.to(self.device)
            
            logger.info("FinBERT模型加载成功")
            
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise
    
    def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """
        分析单段文本的情绪
        
        Args:
            text: 待分析的文本
            
        Returns:
            dict包含:
                - sentiment_score: 情绪得分（-1到1）
                - label: 情绪标签（positive/neutral/negative）
                - confidence: 置信度（0到1）
                
        Example:
            >>> result = analyzer.analyze_sentiment("业绩增长强劲")
            >>> print(result)
            {'sentiment_score': 0.85, 'label': 'positive', 'confidence': 0.92}
        """
        # 处理空文本
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return {
                'sentiment_score': 0.0,
                'label': 'neutral',
                'confidence': 0.0
            }
        
        try:
            # Tokenize文本
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=self.max_length,
                padding='max_length'
            )
            
            # 移动输入到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 禁用梯度计算
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # 获取logits并转换为概率
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
            
            # 获取预测结果
            probs = probabilities[0].cpu().numpy()
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            
            # 提取各类别的概率
            neg_prob = float(probs[0])
            neu_prob = float(probs[1])
            pos_prob = float(probs[2])
            
            # 计算情绪得分（-1到1）
            # 公式：positive_prob - negative_prob
            sentiment_score = pos_prob - neg_prob
            
            # 确定标签
            label = self.LABEL_MAP[predicted_class]
            
            # 置信度为该类别的概率
            confidence = float(probs[predicted_class])
            
            return {
                'sentiment_score': round(sentiment_score, 4),
                'label': label,
                'confidence': round(confidence, 4)
            }
            
        except Exception as e:
            logger.error(f"情绪分析失败: {str(e)}")
            return {
                'sentiment_score': 0.0,
                'label': 'neutral',
                'confidence': 0.0
            }
    
    def batch_analyze(self, texts: List[str]) -> List[Dict[str, any]]:
        """
        批量分析多段文本的情绪
        
        Args:
            texts: 文本列表
            
        Returns:
            结果列表，每个元素与analyze_sentiment返回格式相同
            
        Example:
            >>> results = analyzer.batch_analyze(["业绩好", "业绩差"])
            >>> len(results) == 2
            True
        """
        if not texts:
            return []
        
        results = []
        for i, text in enumerate(texts):
            logger.debug(f"分析第{i+1}/{len(texts)}条文本")
            result = self.analyze_sentiment(text)
            results.append(result)
        
        return results
    
    def analyze_mda_section(self, mda_text: str) -> Dict[str, any]:
        """
        分析MD&A章节的整体情绪
        
        Args:
            mda_text: MD&A完整文本
            
        Returns:
            包含整体情绪和分段情绪的dict
        """
        if not mda_text or not mda_text.strip():
            return {
                'overall_sentiment': 0.0,
                'overall_label': 'neutral',
                'segment_count': 0
            }
        
        # 简单策略：按句号分割成段落，分别分析后取平均
        # 注意：实际应用中可能需要更智能的分段策略
        sentences = [s.strip() for s in mda_text.split('。') if s.strip()]
        
        if not sentences:
            return {
                'overall_sentiment': 0.0,
                'overall_label': 'neutral',
                'segment_count': 0
            }
        
        # 限制段落数量以避免过长处理时间
        max_segments = min(len(sentences), 20)
        segments = sentences[:max_segments]
        
        # 分析每个段落
        segment_results = self.batch_analyze(segments)
        
        # 计算平均情绪得分
        scores = [r['sentiment_score'] for r in segment_results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # 确定整体标签
        if avg_score > 0.2:
            overall_label = 'positive'
        elif avg_score < -0.2:
            overall_label = 'negative'
        else:
            overall_label = 'neutral'
        
        return {
            'overall_sentiment': round(avg_score, 4),
            'overall_label': overall_label,
            'segment_count': len(segment_results),
            'segment_details': segment_results
        }
