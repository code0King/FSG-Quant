"""
多数据源框架快速开始示例

演示如何使用DataSourceManager切换不同的数据源
"""
import sys
from pathlib import Path

# 添加src到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_source_manager import DataSourceManager


def example_1_sqlite_source():
    """示例1: 使用SQLite数据源（默认）"""
    print("=" * 60)
    print("示例1: SQLite数据源")
    print("=" * 60)
    
    # 创建管理器（自动读取config/data_source.yaml）
    manager = DataSourceManager()
    
    # 查看当前配置
    info = manager.get_source_info()
    print(f"\n当前数据源: {info['source_type']}")
    print(f"加载器类型: {info['loader_type']}")
    
    # 加载股票列表
    stocks = manager.get_stock_list()
    if not stocks.empty:
        print(f"\n找到 {len(stocks)} 只股票:")
        print(stocks.to_string(index=False))
    
    # 加载财务数据
    print("\n加载平安银行2023年财务数据:")
    financial = manager.load_financial('000001.SZ', 2023)
    if not financial.empty:
        print(financial[['stock_code', 'report_year', 'revenue', 'net_profit']].to_string(index=False))
    
    return manager


def example_2_csv_source():
    """示例2: 切换到CSV数据源"""
    print("\n" + "=" * 60)
    print("示例2: CSV数据源")
    print("=" * 60)
    
    manager = DataSourceManager()
    
    # 切换到CSV
    print("\n切换到 local_csv 数据源...")
    manager.switch_source('local_csv')
    
    info = manager.get_source_info()
    print(f"当前数据源: {info['source_type']}")
    print(f"加载器类型: {info['loader_type']}")
    
    # 注意：如果没有CSV文件，会返回空DataFrame
    print("\n尝试从CSV加载数据...")
    financial = manager.load_financial()
    
    if financial.empty:
        print("⚠️  未找到CSV数据文件")
        print("\n提示: 请在 data/local/financial/ 目录下放置CSV文件")
        print("文件格式参考: docs/MULTI_DATASOURCE_GUIDE.md")
    else:
        print(f"✅ 成功加载 {len(financial)} 条记录")
        print(financial.head())
    
    return manager


def example_3_compare_sources():
    """示例3: 对比不同数据源"""
    print("\n" + "=" * 60)
    print("示例3: 数据源对比")
    print("=" * 60)
    
    stock_code = '000001.SZ'
    year = 2023
    
    # SQLite数据源
    print("\n1. SQLite数据源:")
    sqlite_mgr = DataSourceManager()
    sqlite_data = sqlite_mgr.load_financial(stock_code, year)
    
    if not sqlite_data.empty:
        print(f"   ✅ 加载成功: {len(sqlite_data)} 条记录")
        print(f"   营收: {sqlite_data['revenue'].values[0]}")
    else:
        print("   ❌ 无数据")
    
    # CSV数据源
    print("\n2. CSV数据源:")
    csv_mgr = DataSourceManager()
    csv_mgr.switch_source('local_csv')
    csv_data = csv_mgr.load_financial(stock_code, year)
    
    if not csv_data.empty:
        print(f"   ✅ 加载成功: {len(csv_data)} 条记录")
        print(f"   营收: {csv_data['revenue'].values[0]}")
    else:
        print("   ⚠️  无数据（需要准备CSV文件）")


def example_4_programmatic_switching():
    """示例4: 编程方式切换数据源"""
    print("\n" + "=" * 60)
    print("示例4: 动态切换数据源")
    print("=" * 60)
    
    manager = DataSourceManager()
    
    # 遍历所有可用的数据源类型
    source_types = ['sqlite', 'local_csv']
    
    for source_type in source_types:
        print(f"\n切换到 {source_type}...")
        try:
            manager.switch_source(source_type)
            info = manager.get_source_info()
            print(f"  ✅ 成功切换")
            print(f"  加载器: {info['loader_type']}")
        except Exception as e:
            print(f"  ❌ 切换失败: {e}")


if __name__ == '__main__':
    print("\n" + "📊 " * 20)
    print("多数据源框架 - 快速开始示例")
    print("📊 " * 20 + "\n")
    
    # 运行示例
    example_1_sqlite_source()
    example_2_csv_source()
    example_3_compare_sources()
    example_4_programmatic_switching()
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 编辑 config/data_source.yaml 配置您的数据源")
    print("2. 准备CSV数据文件（如果使用CSV数据源）")
    print("3. 阅读 docs/MULTI_DATASOURCE_GUIDE.md 了解更多")
    print()
