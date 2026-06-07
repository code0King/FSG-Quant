"""调试审计意见提取"""
import sys
sys.path.insert(0, 'src')
from data_pipeline.pdf_parser import AnnualReportParser, AUDIT_SECTION_TITLES

parser = AnnualReportParser()
path = 'data/raw/annual_reports/000001.SZ/2023.pdf'
result = parser.parse(path)

full_text = result['full_text']

# 检查审计章节提取
for title in AUDIT_SECTION_TITLES:
    idx = full_text.find(title)
    if idx >= 0:
        start = idx + len(title)
        snippet = full_text[start:start+1500]
        print(f'=== {title} (idx={idx}) ===')
        print(snippet[:800])
        print()
        # 检查关键词
        for kw in ['标准无保留意见', '保留意见', '否定意见', '无法表示意见', '无保留意见']:
            if kw in full_text[idx:idx+5000]:
                print(f'  Found: {kw}')
        print()
    else:
        print(f'=== {title} === NOT FOUND')
        print()

# 全文搜索审计关键词
print('=== 全文搜索 ===')
for kw in ['标准无保留意见', '无保留意见', '审计意见', '我们认为']:
    idx = full_text.find(kw)
    if idx >= 0:
        ctx = full_text[max(0,idx-80):idx+120]
        print(f'  Found "{kw}" at {idx}: ...{ctx}...')
    else:
        print(f'  "{kw}" NOT FOUND')
