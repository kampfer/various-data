// domain/ledger/constants.ts
// 领域枚举与边界常量：用 as const + 联合类型替代 enum（isolatedModules 下不使用 const enum）。
// 本文件只定义「码」，不含任何中文展示文案（展示文案见 labels.ts）。

/** 产品类型码全集：WEALTH=理财、FUND=基金、STOCK=股票（需求 1.1、1.2 的预定义取值） */
export const PRODUCT_TYPES = ['WEALTH', 'FUND', 'STOCK'] as const;

/** 产品类型：与后端 ProductType 枚举、`il_transaction.product_type` 列值逐字符一致 */
export type ProductType = typeof PRODUCT_TYPES[number];

/** 交易方向码全集：BUY=买入、SELL=卖出（需求 1.1、1.2 的预定义取值） */
export const TRADE_DIRECTIONS = ['BUY', 'SELL'] as const;

/** 交易方向：与后端 TradeDirection 枚举、`il_transaction.direction` 列值逐字符一致 */
export type TradeDirection = typeof TRADE_DIRECTIONS[number];

/** 需求 2.24 规定必须提供的三个预设页大小，直接喂给 antd Pagination 的 pageSizeOptions */
export const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

/** 默认浏览状态使用的页大小（需求「默认浏览状态」定义中的模块预设页大小） */
export const DEFAULT_PAGE_SIZE = 10;

/** 自定义页大小下界，闭区间（需求 2.25、2.26） */
export const MIN_PAGE_SIZE = 1;

/** 自定义页大小上界，闭区间（需求 2.25、2.26） */
export const MAX_PAGE_SIZE = 100;

/** 两个交易查询模块的标识；账户管理不属于交易查询模型。 */
export type LedgerModule = 'history' | 'holdings';

/** 投资台账导航模块；accounts 仅用于 URL 导航，不进入交易查询状态。 */
export type LedgerNavigationModule = LedgerModule | 'accounts';

/** 排序方向：asc=从小到大，desc=从大到小（需求 2.19） */
export type SortOrder = 'asc' | 'desc';

/** 持仓模块可排序的数值字段：position=持仓（市值），totalProfit=总收益（需求 2.19） */
export type HoldingSortField = 'position' | 'totalProfit';
