// store/ledger/types.ts
// Redux 账本状态契约：只保存 DTO、草稿与 LedgerQuerySnapshot 等可序列化纯数据。
import type { LedgerQuerySnapshot } from '../../domain/ledger/LedgerQueryState';
import type { FieldError } from '../../domain/ledger/TradeDraftValidator';
import type { LedgerModule } from '../../domain/ledger/constants';
import type {
  HoldingOut,
  PortfolioStatisticsOut,
  TradeDraft,
  TransactionOut,
  ValuationDraft,
} from '../../api/types';

/** 列表型模块的通用状态；T 为历史交易或持仓行 DTO。 */
export interface ListSliceState<T> {
  /** 已应用查询的纯数据快照；未提交的筛选输入不写入此处。 */
  query: LedgerQuerySnapshot;
  /** 当前页数据；请求失败时保留旧值。 */
  items: T[];
  /** 分页前结果总数。 */
  total: number;
  /** 后端回显的当前页码，1 起。 */
  page: number;
  /** 后端回显的当前页大小。 */
  pageSize: number;
  /** 总页数；0 表示当前结果没有有效页码。 */
  pageCount: number;
  /** 列表请求是否正在进行。 */
  loading: boolean;
  /** 最近一次列表请求的中文错误；null 表示无错误。 */
  error: string | null;
}

/** 表单弹窗的通用状态；D 为交易或估值草稿。 */
export interface FormSliceState<D> {
  /** 弹窗是否可见。 */
  visible: boolean;
  /** 用户输入的可序列化草稿；校验失败时原样保留。 */
  draft: D;
  /** 前端校验或后端响应返回的字段级错误。 */
  fieldErrors: FieldError[];
  /** 表单是否正在提交，用于阻止重复提交。 */
  submitting: boolean;
}
/** state.ledger 的完整、可序列化状态形状。 */
export interface LedgerState {
  /** 当前模块；null 表示初始模块尚未由 bootstrapLedger 决定。 */
  activeModule: LedgerModule | null;
  /** 初始模块决策请求是否正在进行。 */
  bootstrapping: boolean;
  /** 历史交易记录模块的列表状态。 */
  history: ListSliceState<TransactionOut>;
  /** 持仓模块列表及其组合统计；null 表示统计尚未取得。 */
  holdings: ListSliceState<HoldingOut> & {
    /** 当前已应用持仓查询对应的投资组合统计。 */
    portfolio: PortfolioStatisticsOut | null;
  };
  /** 新建交易表单状态。 */
  tradeForm: FormSliceState<TradeDraft>;
  /** 维护估值表单状态。 */
  valuationForm: FormSliceState<ValuationDraft>;
}

/**
 * thunk 当前所需的最小根状态契约。
 * 待任务 12.4 导出完整 RootState 后，该类型仍与根 store 结构兼容，且不提前改造 store。
 */
export interface LedgerRootState {
  /** 账本切片。 */
  ledger: LedgerState;
}
