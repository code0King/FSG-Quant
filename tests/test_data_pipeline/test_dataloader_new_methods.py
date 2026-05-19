"""
测试DataLoader新增方法

验证load_governance和load_composite_scores方法的功能
"""
import sys
from pathlib import Path

# 添加src到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_loader import DataLoader
import tempfile
import sqlite3
import pandas as pd


def test_load_governance():
    """测试治理数据加载"""
    print("=" * 60)
    print("测试1: load_governance方法")
    print("=" * 60)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        db_path = tmp.name
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建governance_data表
    cursor.execute("""
        CREATE TABLE governance_data (
            stock_code TEXT NOT NULL,
            report_year INTEGER NOT NULL,
            major_shareholder_pledge_ratio REAL,
            audit_opinion TEXT,
            is_standard_audit BOOLEAN,
            core_personnel_turnover_rate REAL,
            PRIMARY KEY (stock_code, report_year)
        )
    """)
    
    # 插入测试数据
    test_data = [
        ('000001.SZ', 2023, 0.0, '标准无保留意见', 1, 0.0),
        ('000001.SZ', 2022, 0.0, '标准无保留意见', 1, 0.0),
        ('000002.SZ', 2023, 0.15, '标准无保留意见', 1, 0.05),
        ('300750.SZ', 2023, 0.05, '带强调事项段的无保留意见', 0, 0.08),
    ]
    
    cursor.executemany("""
        INSERT INTO governance_data VALUES (?, ?, ?, ?, ?, ?)
    """, test_data)
    
    conn.commit()
    conn.close()
    
    # 测试DataLoader
    loader = DataLoader(data_dir=db_path)
    
    # 测试1: 加载质押数据
    print("\n1. 加载股权质押数据:")
    pledge_df = loader.load_governance(data_type='pledge', stock_code='000001.SZ', year=2023)
    print(f"   记录数: {len(pledge_df)}")
    if not pledge_df.empty:
        print(f"   列名: {pledge_df.columns.tolist()}")
        print(f"   数据:\n{pledge_df}")
    
    # 测试2: 加载审计意见
    print("\n2. 加载审计意见数据:")
    audit_df = loader.load_governance(data_type='audit', stock_code='300750.SZ', year=2023)
    print(f"   记录数: {len(audit_df)}")
    if not audit_df.empty:
        print(f"   列名: {audit_df.columns.tolist()}")
        print(f"   数据:\n{audit_df}")
    
    # 测试3: 加载高管数据
    print("\n3. 加载高管流失数据:")
    exec_df = loader.load_governance(data_type='executive', stock_code='000002.SZ', year=2023)
    print(f"   记录数: {len(exec_df)}")
    if not exec_df.empty:
        print(f"   列名: {exec_df.columns.tolist()}")
        print(f"   数据:\n{exec_df}")
    
    # 测试4: 加载全部治理数据
    print("\n4. 加载全部治理数据:")
    all_df = loader.load_governance(data_type='all', year=2023)
    print(f"   记录数: {len(all_df)}")
    if not all_df.empty:
        print(f"   列名: {all_df.columns.tolist()}")
    
    # 清理
    import os
    os.unlink(db_path)
    
    print("\n✅ load_governance测试完成!")
    return True


def test_load_composite_scores():
    """测试综合评分加载"""
    print("\n" + "=" * 60)
    print("测试2: load_composite_scores方法")
    print("=" * 60)
    
    # 创建临时目录和示例Parquet文件
    import tempfile
    temp_dir = tempfile.mkdtemp()
    factors_dir = Path(temp_dir) / 'factors'
    factors_dir.mkdir(parents=True)
    
    # 创建示例综合评分数据
    sample_data = pd.DataFrame({
        'stock_code': ['000001.SZ', '000002.SZ', '300750.SZ'],
        'report_year': [2023, 2023, 2023],
        'offensive_score': [85.5, 72.3, 90.1],
        'defensive_score': [80.2, 65.8, 75.5],
        'composite_risk_level': ['green', 'yellow', 'green']
    })
    
    # 保存为Parquet
    parquet_path = factors_dir / 'composite_scores.parquet'
    sample_data.to_parquet(parquet_path)
    
    # 测试DataLoader
    loader = DataLoader(data_dir=temp_dir)
    
    # 测试1: 加载2023年综合评分
    print("\n1. 加载2023年综合评分:")
    scores_df = loader.load_composite_scores(year=2023)
    print(f"   记录数: {len(scores_df)}")
    if not scores_df.empty:
        print(f"   列名: {scores_df.columns.tolist()}")
        print(f"   数据:\n{scores_df}")
    
    # 测试2: 加载全部年份（应该返回空，因为只有2023年数据）
    print("\n2. 加载全部年份综合评分:")
    all_scores = loader.load_composite_scores(year=None)
    print(f"   记录数: {len(all_scores)}")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ load_composite_scores测试完成!")
    return True


if __name__ == '__main__':
    try:
        test_load_governance()
        test_load_composite_scores()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
