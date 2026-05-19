"""
测试多数据源框架

验证DataSourceManager和CSVDataLoader的功能
"""
import sys
from pathlib import Path
import tempfile
import pandas as pd

# 添加src到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_source_manager import DataSourceManager
from data_pipeline.csv_loader import CSVDataLoader


def test_data_source_manager_sqlite():
    """测试DataSourceManager使用SQLite"""
    print("=" * 60)
    print("测试1: DataSourceManager - SQLite数据源")
    print("=" * 60)
    
    try:
        manager = DataSourceManager()
        info = manager.get_source_info()
        
        print(f"\n当前数据源类型: {info['source_type']}")
        print(f"加载器类型: {info['loader_type']}")
        
        # 测试加载股票列表
        stocks = manager.get_stock_list()
        if not stocks.empty:
            print(f"\n✅ 成功加载 {len(stocks)} 只股票")
            print(stocks.head())
        else:
            print("\n⚠️  未找到股票数据（数据库可能为空）")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_loader_basic():
    """测试CSVDataLoader基本功能"""
    print("\n" + "=" * 60)
    print("测试2: CSVDataLoader - 基本功能")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    financial_dir = Path(temp_dir) / 'financial'
    governance_dir = Path(temp_dir) / 'governance'
    market_dir = Path(temp_dir) / 'market'
    factors_dir = Path(temp_dir) / 'factors'
    
    financial_dir.mkdir(parents=True)
    governance_dir.mkdir(parents=True)
    market_dir.mkdir(parents=True)
    factors_dir.mkdir(parents=True)
    
    # 创建示例CSV文件
    sample_financial = pd.DataFrame({
        'stock_code': ['000001.SZ', '000001.SZ', '000002.SZ'],
        'report_year': [2023, 2022, 2023],
        'revenue': [1500.0, 1400.0, 800.0],
        'net_profit': [150.0, 140.0, 80.0],
        'total_assets': [3000.0, 2800.0, 1600.0],
        'net_assets': [1500.0, 1400.0, 800.0]
    })
    
    csv_path = financial_dir / 'financial_data.csv'
    sample_financial.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n创建示例CSV文件: {csv_path}")
    
    # 初始化CSV加载器
    loader = CSVDataLoader(
        financial_dir=str(financial_dir),
        governance_dir=str(governance_dir),
        market_dir=str(market_dir),
        factors_dir=str(factors_dir)
    )
    
    # 测试1: 加载全部数据
    print("\n1. 加载全部财务数据:")
    df_all = loader.load_financial()
    print(f"   记录数: {len(df_all)}")
    if not df_all.empty:
        print(f"   列名: {df_all.columns.tolist()}")
        print(df_all.head())
    
    # 测试2: 按股票代码过滤
    print("\n2. 加载指定股票数据 (000001.SZ):")
    df_stock = loader.load_financial(stock_code='000001.SZ')
    print(f"   记录数: {len(df_stock)}")
    if not df_stock.empty:
        print(df_stock)
    
    # 测试3: 按年份过滤
    print("\n3. 加载指定年份数据 (2023):")
    df_year = loader.load_financial(year=2023)
    print(f"   记录数: {len(df_year)}")
    if not df_year.empty:
        print(df_year)
    
    # 测试4: 同时按股票和年份过滤
    print("\n4. 加载指定股票和年份 (000001.SZ, 2023):")
    df_both = loader.load_financial(stock_code='000001.SZ', year=2023)
    print(f"   记录数: {len(df_both)}")
    if not df_both.empty:
        print(df_both)
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ CSVDataLoader测试完成!")
    return True


def test_data_source_switching():
    """测试数据源切换"""
    print("\n" + "=" * 60)
    print("测试3: 数据源切换功能")
    print("=" * 60)
    
    try:
        manager = DataSourceManager()
        
        print(f"\n初始数据源: {manager.source_type}")
        
        # 尝试切换到CSV（会因为没有CSV文件而回退）
        print("\n尝试切换到 local_csv...")
        manager.switch_source('local_csv')
        print(f"切换后数据源: {manager.source_type}")
        
        info = manager.get_source_info()
        print(f"加载器类型: {info['loader_type']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "🧪 " * 20)
    print("开始测试多数据源框架")
    print("🧪 " * 20 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("DataSourceManager (SQLite)", test_data_source_manager_sqlite()))
    results.append(("CSVDataLoader", test_csv_loader_basic()))
    results.append(("数据源切换", test_data_source_switching()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:30s} {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        sys.exit(1)
