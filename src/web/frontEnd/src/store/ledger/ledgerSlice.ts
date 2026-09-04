// store/ledger/ledgerSlice.ts
// Redux Toolkit 账本切片：只保存可序列化数据，查询规则统一委托给 LedgerQueryState。
import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { AccountDraft, AccountOut, TradeDraft } from '../../api/types';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import type {
  LedgerQuerySnapshot,
  ProductScope,
} from '../../domain/ledger/LedgerQueryState';
import type { LedgerModule } from '../../domain/ledger/constants';
import * as thunks from './thunks';
import type { LedgerRejectValue } from './thunks';
import type { LedgerState } from './types';

/** 构造空交易草稿；每次调用均返回新的可序列化对象。 */
const createEmptyTradeDraft = (): TradeDraft => ({
  accountId: null,
  productType: null,
  productName: null,
  productCode: null,
  transactionPrice: null,
  transactionQuantity: null,
  direction: null,
  tradeDate: null,
});

/** 构造新建账户的空草稿。 */
const createEmptyAccountDraft = (): AccountDraft => ({
  name: '',
  accountType: '',
  institution: '',
  remark: '',
});

/** 从 thunk 的可序列化拒绝载荷取得用户可见错误。 */
const rejectMessage = (payload: LedgerRejectValue | undefined): string =>
  payload?.message ?? '网络异常，请稍后重试';

const historyQuery = LedgerQueryState.default('history').toSnapshot();
const holdingsQuery = LedgerQueryState.default('holdings').toSnapshot();
/** 账本切片初始状态；类实例只用于生成快照，不进入 Redux state。 */
const initialState: LedgerState = {
  history: {
    query: historyQuery,
    items: [],
    total: 0,
    page: historyQuery.page,
    pageSize: historyQuery.pageSize,
    pageCount: 0,
    loading: false,
    error: null,
  },
  holdings: {
    query: holdingsQuery,
    items: [],
    total: 0,
    page: holdingsQuery.page,
    pageSize: holdingsQuery.pageSize,
    pageCount: 0,
    loading: false,
    error: null,
  },
  tradeForm: {
    visible: false,
    draft: createEmptyTradeDraft(),
    fieldErrors: [],
    submitting: false,
  },
  accounts: {
    items: [],
    loading: false,
    updatingId: null,
    error: null,
  },
  accountForm: {
    visible: false,
    draft: createEmptyAccountDraft(),
    fieldErrors: [],
    submitting: false,
  },
  accountRemarkForm: {
    visible: false,
    accountId: null,
    remark: '',
    fieldErrors: [],
    submitting: false,
  },
};

const ledgerSlice = createSlice({
  name: 'ledger',
  initialState,
  reducers: {
    /** 路由驱动的持仓范围入口：只重置历史查询快照，不写 Redux 模块字段。 */
    openHistoryScope(state, action: PayloadAction<ProductScope>) {
      const query = LedgerQueryState.defaultWithScope('history', action.payload).toSnapshot();
      state.history.query = query;
      state.history.items = [];
      state.history.total = 0;
      state.history.page = query.page;
      state.history.pageSize = query.pageSize;
      state.history.pageCount = 0;
      state.history.loading = false;
      state.history.error = null;
    },

    /** 无上下文历史深链或清除产品范围时恢复历史默认快照，不改变模块字段。 */
    resetHistory(state) {
      const query = LedgerQueryState.default('history').toSnapshot();
      state.history.query = query;
      state.history.items = [];
      state.history.total = 0;
      state.history.page = query.page;
      state.history.pageSize = query.pageSize;
      state.history.pageCount = 0;
      state.history.loading = false;
      state.history.error = null;
    },

    /** 应用已由容器校验通过的条件；页码归一规则由值对象负责（需求 2.27）。 */
    applyQuery(
      state,
      action: PayloadAction<{
        module: LedgerModule;
        patch: Partial<LedgerQuerySnapshot>;
      }>,
    ) {
      const { module, patch } = action.payload;
      state[module].query = LedgerQueryState.from(state[module].query)
        .withFilters(patch)
        .toSnapshot();
    },

    /** 仅改变已校验的页码（需求 2.30）。 */
    changePage(state, action: PayloadAction<{ module: LedgerModule; page: number }>) {
      const { module, page } = action.payload;
      state[module].query = LedgerQueryState.from(state[module].query)
        .withPage(page)
        .toSnapshot();
    },

    /** 改变已校验页大小，并由值对象把页码重置为 1（需求 2.26、2.27）。 */
    changePageSize(state, action: PayloadAction<{ module: LedgerModule; size: number }>) {
      const { module, size } = action.payload;
      state[module].query = LedgerQueryState.from(state[module].query)
        .withPageSize(size)
        .toSnapshot();
    },

    /** 打开新建交易弹窗并清除上次草稿及字段错误。 */
    openTradeForm(state) {
      state.tradeForm.visible = true;
      state.tradeForm.draft = createEmptyTradeDraft();
      state.tradeForm.fieldErrors = [];
      state.tradeForm.submitting = false;
    },

    /** 关闭交易弹窗但保留草稿，便于继续更正。 */
    closeTradeForm(state) {
      state.tradeForm.visible = false;
    },

    /** 合并交易草稿输入；提交失败时原始输入仍留在 state（需求 1.2）。 */
    changeTradeDraft(state, action: PayloadAction<Partial<TradeDraft>>) {
      state.tradeForm.draft = { ...state.tradeForm.draft, ...action.payload };
    },

    /** 打开新建账户弹窗并清除旧草稿。 */
    openAccountForm(state) {
      state.accountForm.visible = true;
      state.accountForm.draft = createEmptyAccountDraft();
      state.accountForm.fieldErrors = [];
      state.accountForm.submitting = false;
    },

    /** 关闭账户创建弹窗但不丢弃草稿，提交失败时可继续修正。 */
    closeAccountForm(state) {
      state.accountForm.visible = false;
    },

    /** 合并账户创建草稿输入。 */
    changeAccountDraft(state, action: PayloadAction<Partial<AccountDraft>>) {
      state.accountForm.draft = { ...state.accountForm.draft, ...action.payload };
    },

    /** 打开备注编辑弹窗；账户身份字段不会进入编辑草稿。 */
    openAccountRemarkForm(state, action: PayloadAction<Pick<AccountOut, 'id' | 'remark'>>) {
      state.accountRemarkForm.visible = true;
      state.accountRemarkForm.accountId = action.payload.id;
      state.accountRemarkForm.remark = action.payload.remark ?? '';
      state.accountRemarkForm.fieldErrors = [];
      state.accountRemarkForm.submitting = false;
    },

    closeAccountRemarkForm(state) {
      state.accountRemarkForm.visible = false;
    },

    changeAccountRemark(state, action: PayloadAction<string>) {
      state.accountRemarkForm.remark = action.payload;
      state.accountRemarkForm.fieldErrors = state.accountRemarkForm.fieldErrors
        .filter((error) => error.field !== 'remark');
    },

  },
  extraReducers: (builder) => {
    builder
      .addCase(thunks.fetchHistory.pending, (state) => {
        state.history.loading = true;
        state.history.error = null;
      })
      .addCase(thunks.fetchHistory.fulfilled, (state, action) => {
        state.history.loading = false;
        state.history.error = null;
        state.history.items = action.payload.items;
        state.history.total = action.payload.total;
        state.history.page = action.payload.page;
        state.history.pageSize = action.payload.pageSize;
        state.history.pageCount = action.payload.pageCount;
      })
      .addCase(thunks.fetchHistory.rejected, (state, action) => {
        state.history.loading = false;
        state.history.error = rejectMessage(action.payload);
      })
      .addCase(thunks.fetchHoldings.pending, (state) => {
        state.holdings.loading = true;
        state.holdings.error = null;
      })
      .addCase(thunks.fetchHoldings.fulfilled, (state, action) => {
        state.holdings.loading = false;
        state.holdings.error = null;
        state.holdings.items = action.payload.items;
        state.holdings.total = action.payload.total;
        state.holdings.page = action.payload.page;
        state.holdings.pageSize = action.payload.pageSize;
        state.holdings.pageCount = action.payload.pageCount;
      })
      .addCase(thunks.fetchHoldings.rejected, (state, action) => {
        state.holdings.loading = false;
        state.holdings.error = rejectMessage(action.payload);
      })
      .addCase(thunks.submitTransaction.pending, (state) => {
        state.tradeForm.submitting = true;
        state.tradeForm.fieldErrors = [];
      })
      .addCase(thunks.submitTransaction.fulfilled, (state) => {
        state.tradeForm.submitting = false;
        state.tradeForm.visible = false;
        state.tradeForm.draft = createEmptyTradeDraft();
        state.tradeForm.fieldErrors = [];
      })
      .addCase(thunks.submitTransaction.rejected, (state, action) => {
        state.tradeForm.submitting = false;
        state.tradeForm.fieldErrors = action.payload?.fieldErrors ?? [];
      })
      .addCase(thunks.removeTransaction.pending, (state) => {
        state.history.loading = true;
        state.history.error = null;
      })
      .addCase(thunks.removeTransaction.fulfilled, (state) => {
        state.history.loading = false;
      })
      .addCase(thunks.removeTransaction.rejected, (state, action) => {
        state.history.loading = false;
        state.history.error = rejectMessage(action.payload);
      })
      .addCase(thunks.fetchAccounts.pending, (state) => {
        state.accounts.loading = true;
        state.accounts.error = null;
      })
      .addCase(thunks.fetchAccounts.fulfilled, (state, action) => {
        state.accounts.loading = false;
        state.accounts.error = null;
        state.accounts.items = action.payload;
      })
      .addCase(thunks.fetchAccounts.rejected, (state, action) => {
        state.accounts.loading = false;
        state.accounts.error = rejectMessage(action.payload);
      })
      .addCase(thunks.updateAccountStatus.pending, (state, action) => {
        state.accounts.updatingId = action.meta.arg.accountId;
        state.accounts.error = null;
      })
      .addCase(thunks.updateAccountStatus.fulfilled, (state) => {
        state.accounts.updatingId = null;
      })
      .addCase(thunks.updateAccountStatus.rejected, (state, action) => {
        state.accounts.updatingId = null;
        state.accounts.error = rejectMessage(action.payload);
      })
      .addCase(thunks.createAccount.pending, (state) => {
        state.accountForm.submitting = true;
        state.accountForm.fieldErrors = [];
      })
      .addCase(thunks.createAccount.fulfilled, (state) => {
        state.accountForm.submitting = false;
        state.accountForm.visible = false;
        state.accountForm.draft = createEmptyAccountDraft();
        state.accountForm.fieldErrors = [];
      })
      .addCase(thunks.createAccount.rejected, (state, action) => {
        state.accountForm.submitting = false;
        state.accountForm.fieldErrors = action.payload?.fieldErrors ?? [];
      })
      .addCase(thunks.updateAccountRemark.pending, (state) => {
        state.accountRemarkForm.submitting = true;
        state.accountRemarkForm.fieldErrors = [];
      })
      .addCase(thunks.updateAccountRemark.fulfilled, (state) => {
        state.accountRemarkForm.submitting = false;
        state.accountRemarkForm.visible = false;
        state.accountRemarkForm.accountId = null;
        state.accountRemarkForm.remark = '';
        state.accountRemarkForm.fieldErrors = [];
      })
      .addCase(thunks.updateAccountRemark.rejected, (state, action) => {
        state.accountRemarkForm.submitting = false;
        state.accountRemarkForm.fieldErrors = action.payload?.fieldErrors ?? [];
      })
  },
});

/** 同步 action creators；查询输入须在容器通过校验后再派发。 */
export const {
  openHistoryScope,
  resetHistory,
  applyQuery,
  changePage,
  changePageSize,
  openTradeForm,
  closeTradeForm,
  changeTradeDraft,
  openAccountForm,
  closeAccountForm,
  changeAccountDraft,
  openAccountRemarkForm,
  closeAccountRemarkForm,
  changeAccountRemark,
} = ledgerSlice.actions;

/** 默认导出 reducer，供任务 12.4 装配到根 store 的 ledger 键。 */
export default ledgerSlice.reducer;
