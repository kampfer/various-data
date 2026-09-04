// 账本 HTTP DTO 镜像：交易数值均为十进制文本，展示标签不进入传输契约。
import type { ProductType, TradeDirection, SortOrder, HoldingSortField } from '../domain/ledger/constants';
export interface ApiEnvelope<T> { code: number; msg: string; data: T | null; }
/** 字段名使用 canonical camelCase，可回填交易表单。 */
export interface FieldErrorItem { field: string; code: string; message: string; }
export interface Metric { available: boolean; value: string | null; unavailableReason: string | null; }
/** 历史交易行：价格、数量使用 canonical 字段，均不做前端数值转换。 */
export interface TransactionOut { id: number; accountId: number | null; accountName: string | null; accountInstitution: string | null; productType: ProductType; productName: string; productCode: string; transactionPrice: string; transactionQuantity: string; fee: string; direction: TradeDirection; tradeDate: string; }
export interface HoldingOut { productType: ProductType; productName: string; productCode: string; position: Metric; positionQuantity: Metric; totalProfit: Metric; totalProfitRate: Metric; annualizedRate: Metric; }
export interface PageOut<T> { items: T[]; total: number; page: number; pageSize: number; pageCount: number; }
/** 基金代码表筛选结果：用于展示并回填交易草稿，不经过 HTTP 传输。 */
export interface FundSearchOut {
  /** 基金名称，<= 100 字符，可直接填入交易草稿的 productName */
  fundName: string;
  /** 基金代码，<= 32 字符，可直接填入交易草稿的 productCode */
  fundCode: string;
}
/** 新交易草稿；所有数值始终保留为原始文本。交易金额不进入草稿，纯前端展示计算。 */
export interface TradeDraft { accountId?: number | null; productType?: ProductType | null; productName?: string | null; productCode?: string | null; transactionPrice?: string | null; transactionQuantity?: string | null; fee?: string | null; direction?: TradeDirection | null; tradeDate?: string | null; }
export interface TransactionQueryParams { productType?: ProductType; direction?: TradeDirection; startDate?: string; endDate?: string; productName?: string; productCode?: string; tradeDateOrder?: SortOrder; scopeProductCode?: string; page?: number; pageSize?: number; }
export interface HoldingQueryParams extends TransactionQueryParams { holdingSortField?: HoldingSortField; holdingSortOrder?: SortOrder; }

/** 投资账户响应 DTO；身份字段由服务端维护，前端只展示不可编辑字段。 */
export interface AccountOut {
  id: number;
  name: string;
  accountType: string;
  institution: string | null;
  isActive: boolean;
  remark: string | null;
  createdAt: string;
  updatedAt: string;
}

/** 创建账户入参；账户创建后仅 remark 允许更新。 */
export interface AccountCreatePayload {
  name: string;
  accountType: string;
  institution?: string | null;
  remark?: string | null;
}

/** 账户备注更新入参；禁止携带其它账户字段。 */
export interface AccountRemarkUpdatePayload {
  remark: string | null;
}

/** 账户启用状态更新入参；禁止携带其它账户字段。 */
export interface AccountStatusUpdatePayload {
  isActive: boolean;
}

/** 账户创建表单草稿；保留字符串输入以便提交失败时原样回填。 */
export interface AccountDraft {
  name: string;
  accountType: string;
  institution: string;
  remark: string;
}
