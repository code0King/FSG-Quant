"""测试 pdf_parser 重构后的新功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_extract_mda_section():
    """MD&A 章节定位正常"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = """
    目录
    第一节 重要提示
    第三节 管理层讨论与分析
    报告期内公司实现营业收入...
    公司主营业务保持稳定增长...
    第四节 公司治理
    """
    mda = p._extract_mda_section(text)
    assert mda is not None
    assert "报告期内" in mda
    assert "公司治理" not in mda


def test_extract_mda_section_董事会报告():
    """回退到董事会报告"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = """
    第X节 董事会报告
    公司整体经营情况回顾...
    第Y节 重要事项
    """
    mda = p._extract_mda_section(text)
    assert mda is not None
    assert "公司整体" in mda


def test_extract_mda_section_not_found():
    """不包含 MD&A 章节时返回 None"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = "只有一些无关文本"
    mda = p._extract_mda_section(text)
    assert mda is None


def test_find_next_section():
    """后续章节定位正常"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = "公司经营情况良好\n第四节 公司治理\n"
    pos = p._find_next_section(text)
    assert pos is not None
    assert pos > 0


def test_section_boundary():
    """章节提取不会越界到下一节"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = "第三节 管理层讨论与分析\n报告期内公司经营情况回顾\n第四节 公司治理\n其他内容"
    mda = p._extract_mda_section(text)
    assert "公司治理" not in (mda or "")
    assert "报告期内" in (mda or "")


def test_audit_opinion_fair_view():
    """审计意见语义推断：公允反映"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    text = "我们认为财务报表在所有重大方面按照企业会计准则的规定编制，公允反映了公司财务状况"
    opinion, is_std = p._identify_audit_opinion(text)
    assert opinion == "标准无保留意见"
    assert is_std is True


def test_audit_opinion_non_standard():
    """非标意见识别"""
    from data_pipeline.pdf_parser import AnnualReportParser
    p = AnnualReportParser()
    for kw, expected in [("保留意见", "保留意见"), ("否定意见", "否定意见"),
                          ("无法表示意见", "无法表示意见"),
                          ("带强调事项段的无保留意见", "带强调事项段的无保留意见")]:
        opinion, is_std = p._identify_audit_opinion(kw)
        assert opinion == expected, f"{kw} → {opinition}"
        assert is_std is False
