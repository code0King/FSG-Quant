"""
PDF年报解析器

从A股上市公司年报PDF中提取结构化数据：
1. 管理层讨论与分析（MD&A）文本
2. 审计意见类型
3. 股权质押比例

使用 pdf_extractor 模块（PDF-Extract-Kit → PyMuPDF 降级）替代直接 PyMuPDF 调用。

用法:
    from data_pipeline.pdf_parser import AnnualReportParser
    parser = AnnualReportParser()
    result = parser.parse('data/raw/annual_reports/000001.SZ/2023.pdf')
"""
import re
import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from data_pipeline.pdf_extractor import extract_text

logger = logging.getLogger(__name__)

# 各章节的中文标题关键词（按优先级排序）
MDA_SECTION_TITLES = [
    '管理层讨论与分析',
    '经营情况讨论与分析',
    '董事会报告',
    '管理层分析与讨论',
]

AUDIT_SECTION_TITLES = [
    '审计报告',
    '财务报表附注',
]

# 审计意见关键词（PDF文本提取可能带"的"字如"标准的无保留意见"）
STANDARD_OPINION_KEYWORDS = ['标准无保留意见']
NON_STANDARD_OPINION_KEYWORDS = {
    '保留意见': '保留意见',
    '否定意见': '否定意见',
    '无法表示意见': '无法表示意见',
    '带强调事项段': '带强调事项段的无保留意见',
}
STANDARD_OPINION_PATTERNS = [
    '标准无保留意见',
    '标准的无保留意见',
    '标准无保留',
    '标准的无保留',
]

# 质押相关关键词
PLEDGE_KEYWORDS = [
    '股权质押', '股份质押', '股票质押', '质押比例', '质押股份',
    '累计质押', '质押率',
]

# MD&A 文本缓存目录
MDA_CACHE_DIR = Path("data/cache/parsed_mda")

# 后续章节标题模式（用于确定 MD&A 章节边界）
NEXT_SECTION_PATTERNS = [
    r'第[一二三四五六七八九十\d]+节\s+',
    r'第[一二三四五六七八九十\d]+章\s+',
    r'[\(（][一二三四五六七八九十\d]+[\)）]',
]


class PDFParseError(Exception):
    """PDF解析异常"""


class AnnualReportParser:
    """年报PDF解析器"""

    def __init__(self, use_pdfplumber: bool = True):
        self.use_pdfplumber = use_pdfplumber

    def parse(self, pdf_path: str) -> Dict:
        """
        解析年报PDF，提取所有结构化数据

        Args:
            pdf_path: PDF文件路径

        Returns:
            dict包含:
            - full_text: 全文文本
            - mda_text: MD&A章节文本
            - audit_opinion: 审计意见
            - is_standard_audit: 是否标准意见
            - pledge_ratio: 质押比例 (百分比或None)
            - metadata: PDF元数据
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        result = {
            'mda_text': '',
            'audit_opinion': None,
            'is_standard_audit': None,
            'pledge_ratio': None,
            'full_text': '',
            'metadata': {},
        }

        full_text = extract_text(pdf_path)
        if not full_text:
            logger.warning(f"Empty text extracted from {pdf_path}")
            return result

        result['full_text'] = full_text

        # 尝试从缓存加载 MD&A（更快）
        mda_text = self._load_mda_cache(pdf_path)
        if mda_text is None:
            mda_text = self._extract_mda_section(full_text)
            if mda_text:
                self._save_mda_cache(pdf_path, mda_text)
        result['mda_text'] = mda_text or ''

        # 将全文空格/换行归一化用于关键词搜索
        flat_text = re.sub(r'[\s\n\r]+', '', full_text)

        audit_section = self._extract_section(full_text, AUDIT_SECTION_TITLES)
        result['audit_opinion'], result['is_standard_audit'] = self._identify_audit_opinion(
            audit_section or flat_text, flat_text
        )
        result['pledge_ratio'] = self._extract_pledge_ratio(full_text)

        logger.info(f"Parsed {pdf_path.name}: "
                    f"MDA={len(result['mda_text'])}chars, "
                    f"audit={result['audit_opinion']}, "
                    f"pledge={result['pledge_ratio']}")
        return result

    # ── 章节定位 ──────────────────────────────────────────────

    def _extract_mda_section(self, text: str) -> Optional[str]:
        """
        提取 MD&A 章节完整文本。

        策略:
          1. 按优先级匹配章节标题
          2. 定位章节起点
          3. 查找下一个同级章节标题作为终点
          4. 无后续章节时取其后 10000 字符
        """
        for title in MDA_SECTION_TITLES:
            idx = text.rfind(title)
            if idx == -1:
                continue
            start = idx + len(title)
            # 查找下一个章节边界
            remaining = text[start:]
            boundary = self._find_next_section(remaining)
            section_text = remaining[:boundary].strip() if boundary else remaining[:10000].strip()
            if section_text:
                logger.debug(f"Found MDA section '{title}' ({len(section_text)} chars)")
                return section_text
        return None

    def _find_next_section(self, text: str) -> Optional[int]:
        """在文本中查找第一个后续章节标题的位置"""
        best_pos = None
        for pattern in NEXT_SECTION_PATTERNS:
            m = re.search(pattern, text)
            if m and (best_pos is None or m.start() < best_pos):
                best_pos = m.start()
        # 排除过近的误匹配（< 50 字符说明可能是页眉或目录）
        if best_pos is not None and best_pos < 50:
            rest = text[best_pos + 10:]
            m2 = re.search(r'第[一二三四五六七八九十\d]+[节章]', rest)
            if m2:
                best_pos = best_pos + 10 + m2.start()
        return best_pos

    def _extract_section(self, text: str, section_titles: list) -> Optional[str]:
        """
        根据章节标题提取对应章节的文本（通用方法）。
        优先取最后一次出现（避免目录误匹配）。
        """
        for title in section_titles:
            idx = text.rfind(title)
            if idx != -1:
                start = idx + len(title)
                section_text = self._extract_until_next_section(text, start)
                logger.debug(f"Found section '{title}' ({len(section_text)} chars)")
                return section_text
        return None

    def _extract_until_next_section(self, text: str, start: int) -> str:
        """从 start 位置提取文本直到下一个章节标题或 10000 字符"""
        remaining = text[start:]
        boundary = self._find_next_section(remaining)
        if boundary is not None:
            return remaining[:boundary].strip()
        return remaining[:10000].strip()

    # ── MD&A 缓存 ──────────────────────────────────────────────

    def _load_mda_cache(self, pdf_path: Path) -> Optional[str]:
        """从缓存加载已提取的 MD&A 文本"""
        cache_file = MDA_CACHE_DIR / f"{pdf_path.parent.name}_{pdf_path.stem}.txt"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")
        return None

    def _save_mda_cache(self, pdf_path: Path, text: str):
        """保存 MD&A 文本到缓存"""
        MDA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = MDA_CACHE_DIR / f"{pdf_path.parent.name}_{pdf_path.stem}.txt"
        cache_file.write_text(text, encoding="utf-8")

    def _identify_audit_opinion(self, section_text: str, full_text: str = ''):
        """
        识别审计意见类型。

        多级判定（从精确到模糊）:
          1. 字面匹配 → "标准无保留意见"/"标准的无保留意见" → 标准
          2. 非标匹配 → "保留意见"/"否定意见"/"无法表示意见"/"强调事项段" → 对应非标
          3. 语义推断 → "公允反映" + "所有重大方面" + "企业会计准则" → 标准
          4. 兜底     → "无保留意见" 出现在审计章节中 → 标准
                       否则 → "未知"
        """
        if not section_text and not full_text:
            return None, None

        search_text = (full_text or '') + (section_text or '')

        # 规则1: 明确的标准无保留意见字眼
        for pattern in STANDARD_OPINION_PATTERNS:
            if pattern in search_text:
                return '标准无保留意见', True

        # 规则2: 明确的非标准意见（先于语义推断，避免误判）
        for keyword, opinion in NON_STANDARD_OPINION_KEYWORDS.items():
            if keyword in search_text and f'无{keyword}' not in search_text:
                return opinion, False

        # 规则3: 语义推断 — "公允反映"+"所有重大方面"+"企业会计准则"
        #         这是审计意见正文的标准措辞，等价于标准无保留意见
        has_fair_view = '公允反映' in search_text
        has_material = '所有重大方面' in search_text
        has_会计准则 = '企业会计准则' in search_text
        if has_fair_view and has_material and has_会计准则:
            return '标准无保留意见', True

        # 规则4: 审计章节中出现"无保留意见" → 标准（已排除非标情况）
        if section_text and '无保留意见' in section_text:
            return '标准无保留意见', True

        return '未知', None

    def _extract_pledge_ratio(self, text: str) -> Optional[float]:
        """从文本中提取股权质押比例"""
        if not text:
            return None

        patterns = [
            r'(?:股权质押|股份质押|股票质押|累计质押)[^。]{5,50}?(\d+\.?\d*)\s*%',
        ]

        for pattern in patterns:
            for m in re.finditer(pattern, text):
                ctx = text[max(0, m.start()-10):m.end()+20]
                # 排除阈值描述（"达到…%以上"）和"不适用"
                if any(kw in ctx for kw in ['以上', '达到', '不适用', '产品', '担保']):
                    continue
                try:
                    ratio = float(m.group(1))
                    if 0 <= ratio <= 100:
                        return ratio
                except ValueError:
                    continue
        return None

    def extract_financial_tables(self, pdf_path: str) -> Dict:
        """尝试提取财务数据表格（需要pdfplumber）"""
        if not self._pdfplumber_available:
            logger.warning("pdfplumber required for table extraction")
            return {}

        try:
            with self.pdfplumber.open(pdf_path) as pdf:
                tables = []
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    tables.extend(page_tables)
            return {'tables_count': len(tables), 'tables': tables[:5]}
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
            return {}


def batch_parse(pdf_dir: str, stock_code: str, years: list) -> Dict:
    """批量解析某只股票多年年报"""
    pdf_dir = Path(pdf_dir)
    parser = AnnualReportParser()
    results = {}
    for year in years:
        pdf_path = pdf_dir / stock_code / f'{year}.pdf'
        if pdf_path.exists():
            results[year] = parser.parse(str(pdf_path))
        else:
            logger.warning(f"PDF not found: {pdf_path}")
    return results


def save_mda_to_db(db_path: str, stock_code: str, year: int, mda_text: str):
    """将MD&A文本保存到数据库"""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mda_text (
                stock_code TEXT NOT NULL,
                report_year INTEGER NOT NULL,
                mda_text TEXT,
                PRIMARY KEY (stock_code, report_year)
            )
        """)
        cursor.execute(
            "INSERT OR REPLACE INTO mda_text VALUES (?, ?, ?)",
            (stock_code, year, mda_text)
        )
        conn.commit()
        conn.close()
        logger.info(f"MD&A text saved: {stock_code} {year} ({len(mda_text)} chars)")
    except Exception as e:
        logger.error(f"Failed to save MD&A: {e}")


def save_governance_from_pdf(db_path: str, stock_code: str, year: int,
                              audit_opinion: str, is_standard: Optional[bool],
                              pledge_ratio: Optional[float],
                              turnover_rate: Optional[float] = None):
    """将PDF提取的治理数据更新到数据库（不覆盖已有的非None值）"""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        turnover = turnover_rate if turnover_rate is not None else 0.0

        # 先查询已有的质押比例，避免 None 覆盖
        cursor.execute(
            "SELECT major_shareholder_pledge_ratio FROM governance_data "
            "WHERE stock_code=? AND report_year=?",
            (stock_code, year)
        )
        existing = cursor.fetchone()
        if existing is not None and existing[0] is not None and pledge_ratio is None:
            pledge_ratio = existing[0]

        cursor.execute("""
            UPDATE governance_data SET
                audit_opinion = ?,
                is_standard_audit = ?,
                major_shareholder_pledge_ratio = ?,
                core_personnel_turnover_rate = ?
            WHERE stock_code = ? AND report_year = ?
        """, (audit_opinion, is_standard, pledge_ratio, turnover, stock_code, year))
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO governance_data
                (stock_code, report_year, audit_opinion, is_standard_audit,
                 major_shareholder_pledge_ratio, core_personnel_turnover_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (stock_code, year, audit_opinion, is_standard, pledge_ratio, turnover))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save governance: {e}")
