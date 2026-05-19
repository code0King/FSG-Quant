"""
创建示例数据库脚本

用于测试和演示，创建包含少量示例数据的SQLite数据库
"""
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_database(db_path: str = 'data/raw/financial_data.sqlite'):
    """
    创建示例SQLite数据库
    
    包含：
    - 3家示例公司
    - 2022-2023年财务数据
    - 涵盖不同行业和质量等级
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating sample database at {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建companies表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            stock_code TEXT PRIMARY KEY,
            stock_name TEXT NOT NULL,
            industry_sw_level1 TEXT
        )
    """)
    
    # 创建financial_annual表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_annual (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            
            -- 利润表
            revenue REAL,
            cost_of_revenue REAL,
            gross_profit REAL,
            net_profit REAL,
            net_profit_deducted REAL,
            rd_expenses REAL,
            
            -- 资产负债表
            total_assets REAL,
            net_assets REAL,
            accounts_receivable REAL,
            inventory REAL,
            goodwill REAL,
            
            -- 现金流量表
            operating_cash_flow REAL,
            capex REAL,
            
            -- 关键指标
            roe REAL,
            roa REAL,
            roic REAL,
            gross_margin REAL,
            
            PRIMARY KEY (stock_code, report_year),
            FOREIGN KEY (stock_code) REFERENCES companies(stock_code)
        )
    """)
    
    # 创建governance_data表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS governance_data (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            
            major_shareholder_pledge_ratio REAL,
            audit_opinion TEXT,
            is_standard_audit BOOLEAN,
            core_personnel_turnover_rate REAL,
            
            PRIMARY KEY (stock_code, report_year),
            FOREIGN KEY (stock_code) REFERENCES companies(stock_code)
        )
    """)
    
    # 插入示例公司
    companies = [
        ('000001.SZ', '平安银行', '银行'),
        ('000002.SZ', '万科A', '房地产'),
        ('300750.SZ', '宁德时代', '电气设备'),
        ('600519.SH', '贵州茅台', '食品饮料'),
        ('000858.SZ', '五粮液', '食品饮料'),
    ]
    
    cursor.executemany(
        "INSERT OR REPLACE INTO companies VALUES (?, ?, ?)",
        companies
    )
    
    # 插入财务数据 - 平安银行（高质量）
    financial_data = [
        # 平安银行 2023
        ('000001.SZ', 2023, 
         1500.0, 900.0, 600.0, 150.0, 145.0, 5.0,  # 利润表
         3000.0, 1500.0, 300.0, 150.0, 50.0,        # 资产负债表
         180.0, 100.0,                                # 现金流量表
         0.10, 0.05, 0.09, 0.40),                    # 关键指标
        
        # 平安银行 2022
        ('000001.SZ', 2022,
         1400.0, 850.0, 550.0, 140.0, 135.0, 4.5,
         2800.0, 1400.0, 280.0, 140.0, 48.0,
         170.0, 95.0,
         0.095, 0.048, 0.085, 0.39),
        
        # 万科A 2023（中等质量）
        ('000002.SZ', 2023,
         800.0, 560.0, 240.0, 80.0, 65.0, 8.0,
         1600.0, 800.0, 200.0, 300.0, 100.0,
         70.0, 120.0,
         0.08, 0.04, 0.07, 0.30),
        
        # 万科A 2022
        ('000002.SZ', 2022,
         750.0, 530.0, 220.0, 75.0, 60.0, 7.5,
         1500.0, 750.0, 190.0, 280.0, 95.0,
         65.0, 110.0,
         0.075, 0.038, 0.065, 0.29),
        
        # 宁德时代 2023（高增长但现金流紧张）
        ('300750.SZ', 2023,
         2000.0, 1600.0, 400.0, 200.0, 150.0, 100.0,
         2500.0, 1000.0, 500.0, 400.0, 80.0,
         100.0, 300.0,
         0.15, 0.06, 0.12, 0.20),
        
        # 宁德时代 2022
        ('300750.SZ', 2022,
         1800.0, 1450.0, 350.0, 180.0, 135.0, 90.0,
         2300.0, 900.0, 450.0, 380.0, 75.0,
         90.0, 280.0,
         0.14, 0.055, 0.11, 0.19),
        
        # 贵州茅台 2023（极高质量）
        ('600519.SH', 2023,
         1200.0, 240.0, 960.0, 600.0, 595.0, 3.0,
         1800.0, 1500.0, 50.0, 200.0, 10.0,
         650.0, 50.0,
         0.35, 0.28, 0.32, 0.80),
        
        # 贵州茅台 2022
        ('600519.SH', 2022,
         1100.0, 220.0, 880.0, 550.0, 545.0, 2.8,
         1700.0, 1400.0, 45.0, 190.0, 9.0,
         600.0, 45.0,
         0.33, 0.26, 0.30, 0.78),
        
        # 五粮液 2023（高质量）
        ('000858.SZ', 2023,
         900.0, 270.0, 630.0, 350.0, 345.0, 5.0,
         1400.0, 1100.0, 80.0, 150.0, 20.0,
         380.0, 60.0,
         0.28, 0.22, 0.25, 0.70),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO financial_annual VALUES 
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, financial_data)
    
    # 插入治理数据
    governance_data = [
        ('000001.SZ', 2023, 0.0, '标准无保留意见', 1, 0.0),
        ('000001.SZ', 2022, 0.0, '标准无保留意见', 1, 0.0),
        ('000002.SZ', 2023, 0.15, '标准无保留意见', 1, 0.05),
        ('000002.SZ', 2022, 0.12, '标准无保留意见', 1, 0.03),
        ('300750.SZ', 2023, 0.05, '标准无保留意见', 1, 0.08),
        ('300750.SZ', 2022, 0.03, '标准无保留意见', 1, 0.05),
        ('600519.SH', 2023, 0.0, '标准无保留意见', 1, 0.0),
        ('600519.SH', 2022, 0.0, '标准无保留意见', 1, 0.0),
        ('000858.SZ', 2023, 0.0, '标准无保留意见', 1, 0.0),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO governance_data VALUES 
        (?, ?, ?, ?, ?, ?)
    """, governance_data)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Sample database created successfully!")
    logger.info(f"  - Companies: {len(companies)}")
    logger.info(f"  - Financial records: {len(financial_data)}")
    logger.info(f"  - Governance records: {len(governance_data)}")


if __name__ == '__main__':
    create_sample_database()
    print("\n✅ 示例数据库创建完成！")
    print("   位置: data/raw/financial_data.sqlite")
    print("\n现在可以运行测试:")
    print("   python -m pytest tests/ -v")
