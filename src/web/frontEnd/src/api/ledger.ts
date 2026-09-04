// api/ledger.ts
// 账本模块唯一 HTTP 出口；交易请求使用 canonical transactionPrice/transactionQuantity。
// 约定：
//   1. 复用 request.ts 的 axios 实例（baseURL 已含 /api/investmentLedger）与 unwrap<T>() 泛型解包，
//      本文件不出现裸 axios、不拼接前缀、不处理错误（失败统一为 LedgerApiError）。
//   2. 刻意**不提供**交易更新函数与按交易标识查询的函数：交易只能新建与删除（需求 1.4），
//      交易标识仅用于删除定位，不作为查询条件（需求 2.23）。
//   3. 查询类函数的参数直接接受 LedgerQueryState.toParams() 的输出（未启用的条件已被省略，
//      不会退化为空值参数，需求 2.16-2.18）。
import http, { unwrap } from './request';
import type {
  ApiEnvelope,
  PageOut,
  TransactionOut,
  HoldingOut,
  TradeDraft,
  TransactionQueryParams,
  HoldingQueryParams,
  AccountCreatePayload,
  AccountOut,
  AccountRemarkUpdatePayload,
} from './types';
import type { LedgerQueryParams } from '../domain/ledger/LedgerQueryState';

/**
 * 历史交易查询入参：既接受精确的 DTO 形状，也接受 `LedgerQueryState.toParams()` 的输出
 * （两者键集合一致，后者的值被放宽为 string | number 以便直接进 query string）。
 */
export type TransactionQueryInput = TransactionQueryParams | LedgerQueryParams;

/** 持仓查询入参：在历史交易条件之上追加持仓数值排序（需求 2.19） */
export type HoldingQueryInput = HoldingQueryParams | LedgerQueryParams;

/**
 * 分页查询历史交易（接口 2：GET /transactions）。
 * @param params 已省略未启用条件的查询参数（枚举为英文码，日期为 YYYY-MM-DD 闭区间）
 * @returns 当前页交易 + total / page / pageSize / pageCount；空结果时 items 为空且 pageCount 为 0（需求 2.22、2.31）
 * @throws LedgerApiError 页码或页大小越界、日期区间非法、网络异常
 */
export const fetchTransactions = (
  params: TransactionQueryInput
): Promise<PageOut<TransactionOut>> =>
  unwrap(http.get<ApiEnvelope<PageOut<TransactionOut>>>('/transactions', { params }));

/**
 * 创建一笔交易（接口 3：POST /transactions）——历史交易模块是唯一写入入口（需求 1.3）。
 * @param payload 已通过 TradeDraftValidator 校验的草稿
 * @returns 落库后的交易记录
 * @throws LedgerApiError 后端二次校验失败时携带 fieldErrors（需求 1.2）；
 *   卖出数量使同产品持仓数量（Σ 买入 − Σ 卖出，含本次）小于 0 时返回 422 +
 *   `fieldErrors` 指向 `transactionQuantity`（code: `INSUFFICIENT_HOLDING`，
 *   message: 「卖出数量超过当前持仓」），不写入记录、不清空草稿（需求 1.3）
 */
export const createTransaction = (payload: TradeDraft): Promise<TransactionOut> =>
  unwrap(http.post<ApiEnvelope<TransactionOut>>('/transactions', payload));

/**
 * 删除一笔交易（接口 4：DELETE /transactions/{transactionId}，需求 1.5）。
 * @param transactionId 来自表格 rowKey 的交易主键（界面不渲染，需求 2.23）
 * @returns null（该接口无业务负载）
 * @throws LedgerApiError 记录不存在时为 HTTP 404 归一后的错误
 */
export const deleteTransaction = (transactionId: number): Promise<null> =>
  unwrap(http.delete<ApiEnvelope<null>>(`/transactions/${transactionId}`));

/**
 * 分页查询持仓条目（接口 5：GET /holdings，只读，需求 2.4-2.8）。
 * @param params 交易筛选/搜索条件 + 持仓排序 + 分页
 * @returns 当前页持仓条目；不可用指标以 Metric.available=false 表达，不以 0 替代（需求 3.9）
 * @throws LedgerApiError 查询参数非法或网络异常
 */
export const fetchHoldings = (params: HoldingQueryInput): Promise<PageOut<HoldingOut>> =>
  unwrap(http.get<ApiEnvelope<PageOut<HoldingOut>>>('/holdings', { params, timeout: 30000 }));

/** 查询全部投资账户；后端按创建时间倒序返回。 */
export const fetchAccounts = (): Promise<AccountOut[]> =>
  unwrap(http.get<ApiEnvelope<AccountOut[]>>('/accounts'));

/** 创建投资账户；账户身份字段创建后不再提供编辑入口。 */
export const createAccount = (payload: AccountCreatePayload): Promise<AccountOut> =>
  unwrap(http.post<ApiEnvelope<AccountOut>>('/accounts', payload));

/** 仅更新账户备注，账户其它字段不会随请求发送。 */
export const updateAccountRemark = (
  accountId: number,
  payload: AccountRemarkUpdatePayload,
): Promise<AccountOut> =>
  unwrap(http.patch<ApiEnvelope<AccountOut>>(`/accounts/${accountId}/remark`, payload));
