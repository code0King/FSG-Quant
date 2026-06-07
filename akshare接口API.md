### 上市公司质押比例[](https://akshare.akfamily.xyz/data/stock/stock.html#id94 "链接到此标题。")

接口: stock\_gpzy\_pledge\_ratio\_em

目标地址: https://data.eastmoney.com/gpzy/pledgeRatio.aspx

描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例

限量: 单次返回指定交易日的所有历史数据; 其中的交易日需要根据网站提供的为准; 请访问 http://data.eastmoney.com/gpzy/pledgeRatio.aspx 查询具体交易日

输入参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| date | str | date="20240906"; 请访问 http://data.eastmoney.com/gpzy/pledgeRatio.aspx 查询具体交易日 |

输出参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| 序号 | int64 | \- |
| 股票代码 | object | \- |
| 股票简称 | object | \- |
| 交易日期 | object | \- |
| 所属行业 | object | \- |
| 质押比例 | float64 | 注意单位: % |
| 质押股数 | float64 | 注意单位: 万股 |
| 质押市值 | float64 | 注意单位: 万元 |
| 质押笔数 | float64 | \- |
| 无限售股质押数 | float64 | 注意单位: 万股 |
| 限售股质押数 | float64 | 注意单位: 万股 |
| 近一年涨跌幅 | float64 | 注意单位: % |
| 所属行业代码 | object | \- |
### 重要股东股权质押明细[](https://akshare.akfamily.xyz/data/stock/stock.html#id95 "链接到此标题。")

接口: stock\_gpzy\_pledge\_ratio\_detail\_em

目标地址: https://data.eastmoney.com/gpzy/pledgeDetail.aspx

描述: 东方财富网-数据中心-特色数据-股权质押-重要股东股权质押明细

限量: 单次所有历史数据, 由于数据量比较大需要等待一定时间

输入参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| \- | \- | \- |

输出参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| 序号 | int64 | \- |
| 股票代码 | object | \- |
| 股票简称 | object | \- |
| 股东名称 | object | \- |
| 质押股份数量 | float64 | 注意单位: 股 |
| 占所持股份比例 | float64 | 注意单位: % |
| 占总股本比例 | float64 | 注意单位: % |
| 质押机构 | object | \- |
| 最新价 | float64 | 注意单位: 元 |
| 质押日收盘价 | float64 | 注意单位: 元 |
| 预估平仓线 | float64 | 注意单位: 元 |
| 公告日期 | object | \- |
| 质押开始日期 | object | \- |
| 质押结束日期 | object | \- |
| 状态 | object | \- |

### 个股重要股东股权质押明细[](https://akshare.akfamily.xyz/data/stock/stock.html#id96 "链接到此标题。")

接口: stock\_gpzy\_individual\_pledge\_ratio\_detail\_em

目标地址: https://data.eastmoney.com/gpzy/detail/{symbol}.html

描述: 东方财富网-数据中心-股权质押-个股

限量: 单次所有历史数据

输入参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| symbol | str | symbol="603132" |

输出参数

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| 序号 | int64 | \- |
| 股票代码 | object | \- |
| 股票简称 | object | \- |
| 股东名称 | object | \- |
| 质押股份数量 | float64 | 注意单位: 股 |
| 占所持股份比例 | float64 | 注意单位: % |
| 占总股本比例 | float64 | 注意单位: % |
| 质押机构 | object | \- |
| 最新价 | float64 | 注意单位: 元 |
| 质押日收盘价 | float64 | 注意单位: 元 |
| 预估平仓线 | float64 | 注意单位: 元 |
| 公告日期 | object | \- |
| 质押开始日期 | object | \- |
| 质押结束日期 | object | \- |
| 状态 | object | \- |

