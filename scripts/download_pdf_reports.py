"""
从巨潮资讯网(cninfo.com.cn)下载A股上市公司年报PDF

核心流程:
  1. 从 szse_stock.json 获取 stock->orgId 映射
  2. 用 hisAnnouncement/query API 搜索年报公告
  3. 从公告的 adjunctUrl 构建 PDF 下载链接

用法:
    python scripts/download_pdf_reports.py --stocks 000001.SZ 600519.SH --years 2023
    python scripts/download_pdf_reports.py --sample 5 --years 2021 2022 2023
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/raw/annual_reports")
CNINFO_STOCK_URL = "http://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_PDF_URL = "http://static.cninfo.com.cn/{adjunct_path}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "http://www.cninfo.com.cn/",
    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
}


def get_stock_org_id_map() -> Dict[str, str]:
    """从cninfo的stock json获取股票代码 -> orgId 映射"""
    resp = requests.get(CNINFO_STOCK_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {item['code']: item['orgId'] for item in data['stockList']}


def search_annual_reports(symbol: str, org_id: str, year: int) -> List[dict]:
    """
    搜索某股票某年的年报公告列表。
    年报一般在次年3-4月发布，因此搜索日期用 year+1。
    """
    pub_year = year + 1
    se_date = f"{pub_year}-01-01~{pub_year}-12-31"
    payload = {
        "pageNum": "1",
        "pageSize": "30",
        "column": "szse",
        "tabName": "fulltext",
        "plate": "",
        "stock": f"{symbol},{org_id}",
        "searchkey": "",
        "secid": "",
        "category": "category_ndbg_szsh",
        "trade": "",
        "seDate": se_date,
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }

    try:
        resp = requests.post(CNINFO_QUERY_URL, data=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        announcements = result.get('announcements', [])
        logger.info(f"Found {len(announcements)} announcements for {symbol} (FY{year})")
        return announcements
    except Exception as e:
        logger.error(f"Search failed for {symbol} FY{year}: {e}")
        return []


def find_pdf_announcement(announcements: List[dict], year: int) -> Optional[dict]:
    """从公告列表中找年度报告全文PDF（优先中文版，排除摘要和英文版）"""
    year_str = str(year)

    # 1. 中文全文：标题含年份+"年度报告"+"全文"或"报告"，不含"摘要"和"英文"
    for ann in announcements:
        title = ann.get('announcementTitle', '')
        if (year_str in title and '年度报告' in title
                and '摘要' not in title and '英文' not in title
                and 'English' not in title):
            return ann

    # 2. 放宽：不含"摘要"和"英文"
    for ann in announcements:
        title = ann.get('announcementTitle', '')
        if (year_str in title and '年度报告' in title
                and '摘要' not in title and '英文' not in title):
            return ann

    # 3. 接受英文版（兜底）
    for ann in announcements:
        title = ann.get('announcementTitle', '')
        if year_str in title and '年度报告' in title and '摘要' not in title:
            return ann

    return announcements[0] if announcements else None


def download_pdf(pdf_url: str, save_path: Path) -> bool:
    """下载PDF文件到本地"""
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if save_path.exists() and save_path.stat().st_size > 10000:
        logger.info(f"Already exists: {save_path.name} ({save_path.stat().st_size // 1024}KB)")
        return True

    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=120)
        resp.raise_for_status()

        if len(resp.content) < 1000:
            logger.warning(f"File too small ({len(resp.content)} bytes)")
            return False

        save_path.write_bytes(resp.content)
        logger.info(f"Downloaded: {save_path.name} ({len(resp.content)//1024}KB)")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def download_annual_report(symbol: str, org_id: str, year: int, output_dir: str = None, stock_suffix: str = "SZ") -> Optional[Path]:
    """下载某股票某年的年报PDF"""
    output_dir = Path(output_dir or OUTPUT_DIR)
    save_path = output_dir / f"{symbol}.{stock_suffix}" / f"{year}.pdf"

    if save_path.exists() and save_path.stat().st_size > 10000:
        logger.info(f"Already exists: {save_path.name} ({save_path.stat().st_size // 1024}KB)")
        return save_path

    announcements = search_annual_reports(symbol, org_id, year)
    if not announcements:
        return None

    target = find_pdf_announcement(announcements, year)
    if not target:
        logger.warning(f"No annual report found for {symbol} FY{year}")
        return None

    adjunct_url = target.get('adjunctUrl', '')
    title = target.get('announcementTitle', '')

    if not adjunct_url:
        logger.warning(f"No adjunctUrl in announcement: {title}")
        return None

    if not adjunct_url.startswith('http'):
        pdf_url = CNINFO_PDF_URL.format(adjunct_path=adjunct_url)
    else:
        pdf_url = adjunct_url

    logger.info(f"Target: [{title}] -> {adjunct_url}")
    success = download_pdf(pdf_url, save_path)
    return save_path if success else None


def main():
    parser = argparse.ArgumentParser(description='从巨潮资讯网下载年报PDF')
    parser.add_argument('--stocks', nargs='+', default=None, help='股票代码，如 000001.SZ')
    parser.add_argument('--years', nargs='+', type=int, default=[2023], help='财年 (default: 2023)')
    parser.add_argument('--sample', type=int, default=None, help='从SQLite随机选N只股票')
    parser.add_argument('--output-dir', default=str(OUTPUT_DIR), help='输出目录')
    parser.add_argument('--delay', type=float, default=2.0, help='请求间隔(秒)')

    args = parser.parse_args()

    # 确定股票列表（保留后缀）
    if args.stocks:
        stock_list = [(s.split('.')[0], s.split('.')[1]) for s in args.stocks]
    elif args.sample:
        import sqlite3
        conn = sqlite3.connect('data/raw/financial_data.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT stock_code FROM financial_annual LIMIT ?", (args.sample,))
        raw = [r[0] for r in cursor.fetchall()]
        stock_list = [(s.split('.')[0], s.split('.')[1]) for s in raw]
        conn.close()
    else:
        stock_list = [('000001', 'SZ'), ('000002', 'SZ'), ('600519', 'SH'), ('300750', 'SZ'), ('000858', 'SZ')]

    years = sorted(set(args.years))

    # 获取orgId映射
    logger.info("Loading stock->orgId map from cninfo...")
    org_id_map = get_stock_org_id_map()
    logger.info(f"Loaded {len(org_id_map)} stock mappings")

    results = {'success': 0, 'failed': 0, 'missing_orgid': 0}
    for symbol, suffix in stock_list:
        if symbol not in org_id_map:
            logger.warning(f"No orgId for {symbol}, trying gssz prefix")
            org_id = f"gssz{symbol.lstrip('0')}"
        else:
            org_id = org_id_map[symbol]

        for year in years:
            logger.info(f"--- {symbol}.{suffix} FY{year} ---")
            result = download_annual_report(symbol, org_id, year, args.output_dir, suffix)
            if result:
                results['success'] += 1
            else:
                results['failed'] += 1

    logger.info(f"\n{'='*40}")
    logger.info(f"Done: {results['success']} success, {results['failed']} failed")
    logger.info(f"PDF directory: {args.output_dir}/")


if __name__ == '__main__':
    main()
