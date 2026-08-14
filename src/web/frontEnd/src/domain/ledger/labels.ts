// domain/ledger/labels.ts
// 展示标签映射层（presentation-only）：把英文码翻译为界面中文文案。
// 只被展示层/容器层引用；领域计算、API 负载、持久化一律使用码，不使用本文件的值。
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';
import type { ProductType, TradeDirection } from './constants';

/**
 * 产品类型的中文展示名。
 * 使用 Record<ProductType, string> 而非索引签名：新增类型码时缺少映射会**编译期报错**，
 * 从而保证映射对枚举全集穷尽（不会出现界面上显示原始码的情况）。
 */
export const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
  WEALTH: '理财',
  FUND: '基金',
  STOCK: '股票',
};

/** 交易方向的中文展示名，穷尽性同上 */
export const TRADE_DIRECTION_LABELS: Record<TradeDirection, string> = {
  BUY: '买入',
  SELL: '卖出',
};

/** antd Select / Radio 的选项类型：value 为码（进入 query 与请求体），label 为中文（仅渲染） */
export interface LabeledOption<T extends string> {
  readonly value: T;
  readonly label: string;
}

/** 由码全集 + 标签映射生成产品类型下拉选项，保证选项顺序与码全集声明顺序一致 */
export const productTypeOptions = (): readonly LabeledOption<ProductType>[] =>
  PRODUCT_TYPES.map((value) => ({ value, label: PRODUCT_TYPE_LABELS[value] }));

/** 由码全集 + 标签映射生成交易方向下拉选项 */
export const tradeDirectionOptions = (): readonly LabeledOption<TradeDirection>[] =>
  TRADE_DIRECTIONS.map((value) => ({ value, label: TRADE_DIRECTION_LABELS[value] }));
