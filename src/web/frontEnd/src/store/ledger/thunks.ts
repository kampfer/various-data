// store/ledger/thunks.ts
// 账本异步用例：请求参数只从 Redux 中的查询快照派生，不把领域类实例写入 state。
import { createAsyncThunk } from '@reduxjs/toolkit';
import * as ledgerApi from '../../api/ledger';
import { LedgerApiError } from '../../api/request';
import type {
  AccountCreatePayload,
  AccountOut,
  AccountRemarkUpdatePayload,
  HoldingOut,
  PageOut,
  TradeDraft,
  TransactionOut,
} from '../../api/types';
import AccountDraftValidator from '../../domain/ledger/AccountDraftValidator';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import TradeDraftValidator from '../../domain/ledger/TradeDraftValidator';
import type { FieldError } from '../../domain/ledger/TradeDraftValidator';
import type { LedgerRootState } from './types';

/** thunk 失败载荷：提供用户提示，并可携带字段级错误供表单回填。 */
export interface LedgerRejectValue {
  /** 面向用户的中文错误提示。 */
  message: string;
  /** 表单字段错误；非表单请求通常省略。 */
  fieldErrors?: FieldError[];
}

/** 本任务所需的 createAsyncThunk 公共类型配置。 */
type ThunkConfig = {
  /** 当前只依赖 ledger 子树，避免提前执行任务 12.4 的根 store 迁移。 */
  state: LedgerRootState;
  /** 所有已知失败均以统一载荷拒绝。 */
  rejectValue: LedgerRejectValue;
};

/** 把 API 异常转换为可序列化的 thunk 拒绝载荷。 */
const toRejectValue = (error: unknown): LedgerRejectValue => {
  if (error instanceof LedgerApiError) {
    return {
      message: error.message,
      fieldErrors: error.fieldErrors.map(({ field, code, message }) => ({ field, code, message })),
    };
  }
  return {
    message: error instanceof Error && error.message ? error.message : '网络异常，请稍后重试',
  };
};

/** 依据已应用历史查询快照拉取当前页交易（需求 2.14）。 */
export const fetchHistory = createAsyncThunk<PageOut<TransactionOut>, void, ThunkConfig>(
  'ledger/fetchHistory',
  async (_, { getState, rejectWithValue }) => {
    const params = LedgerQueryState.from(getState().ledger.history.query).toParams();
    try {
      return await ledgerApi.fetchTransactions(params);
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);


/** 依据已应用持仓查询快照拉取当前页。 */
export const fetchHoldings = createAsyncThunk<PageOut<HoldingOut>, void, ThunkConfig>(
  'ledger/fetchHoldings',
  async (_, { getState, rejectWithValue }) => {
    const params = LedgerQueryState.from(getState().ledger.holdings.query).toParams();
    try {
      return await ledgerApi.fetchHoldings(params);
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);

/** 创建交易；前端校验失败时不发 HTTP 请求，成功后按已应用查询刷新历史列表。 */
export const submitTransaction = createAsyncThunk<TransactionOut, TradeDraft, ThunkConfig>(
  'ledger/submitTransaction',
  async (draft, { dispatch, rejectWithValue }) => {
    const validation = new TradeDraftValidator().validate(draft);
    if (!validation.valid) {
      return rejectWithValue({
        message: '提交的信息有误，请检查后重试',
        fieldErrors: [...validation.fieldErrors],
      });
    }
    try {
      const created = await ledgerApi.createTransaction(draft);
      await dispatch(fetchHistory());
      return created;
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);
/** 删除交易；成功后重新查询当前历史页，避免本地删行造成分页错位。 */
export const removeTransaction = createAsyncThunk<void, number, ThunkConfig>(
  'ledger/removeTransaction',
  async (transactionId, { dispatch, rejectWithValue }) => {
    try {
      await ledgerApi.deleteTransaction(transactionId);
      await dispatch(fetchHistory());
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);


/** 设计文档旧命名兼容：与 submitTransaction 是同一 thunk，不生成重复 action。 */
export const submitTrade = submitTransaction;

/** 设计文档旧命名兼容：与 removeTransaction 是同一 thunk，不生成重复 action。 */
export const deleteTrade = removeTransaction;

/** 拉取全部投资账户；账户接口不使用交易分页查询参数。 */
export const fetchAccounts = createAsyncThunk<AccountOut[], void, ThunkConfig>(
  'ledger/fetchAccounts',
  async (_, { rejectWithValue }) => {
    try {
      return await ledgerApi.fetchAccounts();
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);

/** 创建账户；校验失败时保留原始草稿，成功后重新拉取服务端排序后的列表。 */
export const createAccount = createAsyncThunk<AccountOut, AccountCreatePayload, ThunkConfig>(
  'ledger/createAccount',
  async (payload, { dispatch, rejectWithValue }) => {
    const draft = {
      name: payload.name,
      accountType: payload.accountType,
      institution: payload.institution ?? '',
      remark: payload.remark ?? '',
    };
    const validation = new AccountDraftValidator().validateCreate(draft);
    if (!validation.valid) {
      return rejectWithValue({
        message: '账户信息有误，请检查后重试',
        fieldErrors: [...validation.fieldErrors],
      });
    }
    try {
      const created = await ledgerApi.createAccount(payload);
      await dispatch(fetchAccounts());
      return created;
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);

/** 仅更新 remark；成功后重新拉取列表，避免覆盖服务端的更新时间和排序结果。 */
export const updateAccountRemark = createAsyncThunk<
  AccountOut,
  { accountId: number; payload: AccountRemarkUpdatePayload },
  ThunkConfig
>(
  'ledger/updateAccountRemark',
  async ({ accountId, payload }, { dispatch, rejectWithValue }) => {
    const validation = new AccountDraftValidator().validateRemark(payload.remark);
    if (!validation.valid) {
      return rejectWithValue({
        message: '备注内容有误，请检查后重试',
        fieldErrors: [...validation.fieldErrors],
      });
    }
    try {
      const updated = await ledgerApi.updateAccountRemark(accountId, payload);
      await dispatch(fetchAccounts());
      return updated;
    } catch (error) {
      return rejectWithValue(toRejectValue(error));
    }
  },
);
