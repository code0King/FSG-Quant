"""
FinBERTAnalyzer单元测试

测试目标：
1. 正确初始化模型
2. 正确分析正面情绪文本
3. 正确分析负面情绪文本
4. 正确分析中性情绪文本
5. 返回正确的数据结构
6. 处理空文本和异常输入
7. 批量分析功能

注意：由于FinBERT模型较大且存在依赖问题，所有测试均使用Mock
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestFinBERTAnalyzer:
    """FinBERT分析器测试类"""
    
    @pytest.fixture
    def analyzer_with_mock(self):
        """创建使用Mock的analyzer（完全Mock，不加载真实模型）"""
        # 先Mock torch和transformers模块
        mock_torch = MagicMock()
        mock_torch.device = lambda x: 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad = MagicMock
        
        # Mock argmax返回一个tensor-like对象
        mock_argmax_result = MagicMock()
        mock_argmax_result.item.return_value = 2  # positive class
        mock_torch.argmax.return_value = mock_argmax_result
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': MagicMock(to=lambda device: MagicMock()),
            'attention_mask': MagicMock(to=lambda device: MagicMock())
        }
        
        mock_model = MagicMock()
        mock_output = MagicMock()
        mock_output.logits = [[-1.0, -0.5, 1.5]]
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model.to = MagicMock()
        
        # Mock softmax返回概率数组
        mock_probs_tensor = MagicMock()
        mock_probs_row = MagicMock()
        mock_probs_row.cpu.return_value.numpy.return_value = [0.1, 0.2, 0.7]
        mock_probs_tensor.__getitem__ = lambda self, idx: mock_probs_row if idx == 0 else MagicMock()
        mock_torch.softmax.return_value = mock_probs_tensor
        
        with patch.dict('sys.modules', {
            'torch': mock_torch,
            'transformers': MagicMock(
                AutoTokenizer=MagicMock(from_pretrained=MagicMock(return_value=mock_tokenizer)),
                AutoModelForSequenceClassification=MagicMock(from_pretrained=MagicMock(return_value=mock_model))
            )
        }):
            from nlp.finbert_analyzer import FinBERTAnalyzer
            analyzer = FinBERTAnalyzer(model_name="test-model")
            analyzer.tokenizer = mock_tokenizer
            analyzer.model = mock_model
            return analyzer
    
    def test_initialization(self, analyzer_with_mock):
        """测试模型初始化"""
        assert analyzer_with_mock is not None
        assert hasattr(analyzer_with_mock, 'tokenizer')
        assert hasattr(analyzer_with_mock, 'model')
    
    def test_analyze_positive_sentiment(self, analyzer_with_mock):
        """测试正面情绪分析"""
        text = "公司业绩大幅增长，盈利能力显著提升，未来发展可期。"
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        assert isinstance(result, dict)
        assert 'sentiment_score' in result
        assert 'label' in result
        assert 'confidence' in result
        
        # 正面情绪应该得分>0
        assert result['sentiment_score'] > 0
        assert result['label'] == 'positive'
    
    def test_analyze_negative_sentiment(self):
        """测试负面情绪分析"""
        # 创建返回负面情绪的mock
        mock_torch = MagicMock()
        mock_torch.device = lambda x: 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad = MagicMock
        
        # Mock argmax返回negative class (0)
        mock_argmax_result = MagicMock()
        mock_argmax_result.item.return_value = 0
        mock_torch.argmax.return_value = mock_argmax_result
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': MagicMock(to=lambda device: MagicMock()),
            'attention_mask': MagicMock(to=lambda device: MagicMock())
        }
        
        mock_model = MagicMock()
        mock_output = MagicMock()
        mock_output.logits = [[1.5, 0.5, -1.0]]  # negative概率高
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model.to = MagicMock()
        
        # Mock softmax输出：negative=0.7, neutral=0.2, positive=0.1
        mock_probs_tensor = MagicMock()
        mock_probs_row = MagicMock()
        mock_probs_row.cpu.return_value.numpy.return_value = [0.7, 0.2, 0.1]
        mock_probs_tensor.__getitem__ = lambda self, idx: mock_probs_row if idx == 0 else MagicMock()
        mock_torch.softmax.return_value = mock_probs_tensor
        
        with patch.dict('sys.modules', {
            'torch': mock_torch,
            'transformers': MagicMock(
                AutoTokenizer=MagicMock(from_pretrained=MagicMock(return_value=mock_tokenizer)),
                AutoModelForSequenceClassification=MagicMock(from_pretrained=MagicMock(return_value=mock_model))
            )
        }):
            from nlp.finbert_analyzer import FinBERTAnalyzer
            analyzer = FinBERTAnalyzer(model_name="test-model")
            analyzer.tokenizer = mock_tokenizer
            analyzer.model = mock_model
            
            text = "公司业绩下滑，面临严峻挑战，经营风险增加。"
            result = analyzer.analyze_sentiment(text)
            
            assert result['sentiment_score'] < 0
            assert result['label'] == 'negative'
    
    def test_analyze_neutral_sentiment(self):
        """测试中性情绪分析"""
        # 创建返回中性情绪的mock
        mock_torch = MagicMock()
        mock_torch.device = lambda x: 'cpu'
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad = MagicMock
        
        # Mock argmax返回neutral class (1)
        mock_argmax_result = MagicMock()
        mock_argmax_result.item.return_value = 1
        mock_torch.argmax.return_value = mock_argmax_result
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': MagicMock(to=lambda device: MagicMock()),
            'attention_mask': MagicMock(to=lambda device: MagicMock())
        }
        
        mock_model = MagicMock()
        mock_output = MagicMock()
        mock_output.logits = [[0.0, 0.1, 0.0]]  # neutral略高
        mock_model.return_value = mock_output
        mock_model.eval = MagicMock()
        mock_model.to = MagicMock()
        
        # Mock softmax输出：negative=0.3, neutral=0.4, positive=0.3
        mock_probs_tensor = MagicMock()
        mock_probs_row = MagicMock()
        mock_probs_row.cpu.return_value.numpy.return_value = [0.3, 0.4, 0.3]
        mock_probs_tensor.__getitem__ = lambda self, idx: mock_probs_row if idx == 0 else MagicMock()
        mock_torch.softmax.return_value = mock_probs_tensor
        
        with patch.dict('sys.modules', {
            'torch': mock_torch,
            'transformers': MagicMock(
                AutoTokenizer=MagicMock(from_pretrained=MagicMock(return_value=mock_tokenizer)),
                AutoModelForSequenceClassification=MagicMock(from_pretrained=MagicMock(return_value=mock_model))
            )
        }):
            from nlp.finbert_analyzer import FinBERTAnalyzer
            analyzer = FinBERTAnalyzer(model_name="test-model")
            analyzer.tokenizer = mock_tokenizer
            analyzer.model = mock_model
            
            text = "公司发布了年度报告，披露了相关财务数据。"
            result = analyzer.analyze_sentiment(text)
            
            # 中性情绪得分接近0
            assert abs(result['sentiment_score']) < 0.3
            assert result['label'] == 'neutral'
    
    def test_result_structure(self, analyzer_with_mock):
        """测试结果结构完整性"""
        text = "测试文本"
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        required_fields = ['sentiment_score', 'label', 'confidence']
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_sentiment_score_range(self, analyzer_with_mock):
        """测试情绪得分范围（-1到1）"""
        text = "测试文本"
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        assert -1 <= result['sentiment_score'] <= 1
    
    def test_confidence_range(self, analyzer_with_mock):
        """测试置信度范围（0到1）"""
        text = "测试文本"
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        assert 0 <= result['confidence'] <= 1
    
    def test_label_values(self, analyzer_with_mock):
        """测试标签值的有效性"""
        text = "测试文本"
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        assert result['label'] in ['positive', 'neutral', 'negative']
    
    def test_empty_text_handling(self, analyzer_with_mock):
        """测试空文本处理"""
        text = ""
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        # 应该有合理的默认值或错误处理
        assert isinstance(result, dict)
    
    def test_long_text_truncation(self, analyzer_with_mock):
        """测试长文本截断"""
        # 创建超过512字符的文本
        text = "这是一个测试句子。" * 100
        
        result = analyzer_with_mock.analyze_sentiment(text)
        
        # 应该能正常处理（内部会截断）
        assert isinstance(result, dict)
        assert 'sentiment_score' in result
    
    def test_batch_analyze(self, analyzer_with_mock):
        """测试批量分析"""
        texts = [
            "公司业绩增长",
            "面临经营挑战",
            "发布年度报告"
        ]
        
        results = analyzer_with_mock.batch_analyze(texts)
        
        assert isinstance(results, list)
        assert len(results) == 3
        
        for result in results:
            assert 'sentiment_score' in result
            assert 'label' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
