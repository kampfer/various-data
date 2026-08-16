// 仅用于展示的中文标签映射；绝不作为 DTO、状态或持久化字段名。
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';
import type { ProductType, TradeDirection } from './constants';
export const PRODUCT_TYPE_LABELS: Record<ProductType, string> = { WEALTH: '理财', FUND: '基金', STOCK: '股票' };
export const TRADE_DIRECTION_LABELS: Record<TradeDirection, string> = { BUY: '买入', SELL: '卖出' };
/** 按产品类型显示交易字段的用户可见名称。 */
export const TRADE_VALUE_LABELS: Record<ProductType, { readonly price: string; readonly quantity: string }> = {
  WEALTH: { price: '净值', quantity: '份额' }, FUND: { price: '净值', quantity: '份额' }, STOCK: { price: '单价', quantity: '数量' },
};
export interface LabeledOption<T extends string> { readonly value: T; readonly label: string; }
export const productTypeOptions = (): readonly LabeledOption<ProductType>[] => PRODUCT_TYPES.map((value) => ({ value, label: PRODUCT_TYPE_LABELS[value] }));
export const tradeDirectionOptions = (): readonly LabeledOption<TradeDirection>[] => TRADE_DIRECTIONS.map((value) => ({ value, label: TRADE_DIRECTION_LABELS[value] }));
