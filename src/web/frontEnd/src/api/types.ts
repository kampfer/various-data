// 账本 HTTP DTO 镜像：交易数值均为十进制文本，展示标签不进入传输契约。
import type { ProductType, TradeDirection, SortOrder, HoldingSortField, LedgerModule } from '../domain/ledger/constants';
export interface ApiEnvelope<T> { code: number; msg: string; data: T | null; }
/** 字段名使用 canonical camelCase，可回填交易表单。 */
export interface FieldErrorItem { field: string; code: string; message: string; }
export interface Metric { available: boolean; value: string | null; unavailableReason: string | null; }
/** 历史交易行：价格、数量使用 canonical 字段，均不做前端数值转换。 */
export interface TransactionOut { id: number; productType: ProductType; productName: string; productCode: string; transactionPrice: string; transactionQuantity: string; direction: TradeDirection; tradeDate: string; }
export interface HoldingOut { productType: ProductType; productName: string; productCode: string; position: Metric; positionQuantity: Metric; totalProfit: Metric; totalProfitRate: Metric; annualizedRate: Metric; }
export interface PageOut<T> { items: T[]; total: number; page: number; pageSize: number; pageCount: number; }
export interface PortfolioStatisticsOut { totalPosition: Metric; totalProfit: Metric; totalProfitRate: Metric; totalAnnualizedRate: Metric; }
export interface InitialModuleOut { module: LedgerModule; }
/**
 * 单条基金搜索结果：仅承载展示与填充所需的两个字段（需求 5.2）。
 * 不携带第三方原始富文本或内部标识；选中后可直接回填交易草稿。
 */
export interface FundSearchOut {
  /** 基金名称，<= 100 字符，可直接填入交易草稿的 productName */
  fundName: string;
  /** 基金代码，<= 32 字符，可直接填入交易草稿的 productCode */
  fundCode: string;
}
/** 新交易草稿；所有数值始终保留为原始文本。 */
export interface TradeDraft { productType?: ProductType | null; productName?: string | null; productCode?: string | null; transactionPrice?: string | null; transactionQuantity?: string | null; direction?: TradeDirection | null; tradeDate?: string | null; }
export interface TransactionQueryParams { productType?: ProductType; direction?: TradeDirection; startDate?: string; endDate?: string; productName?: string; productCode?: string; tradeDateOrder?: SortOrder; scopeProductCode?: string; page?: number; pageSize?: number; }
export interface HoldingQueryParams extends TransactionQueryParams { holdingSortField?: HoldingSortField; holdingSortOrder?: SortOrder; }
