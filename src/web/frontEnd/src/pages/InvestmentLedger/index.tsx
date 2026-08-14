import React from 'react';
import { Button, Skeleton, message } from 'antd';
import { connect } from 'react-redux';
import type { RootState, AppDispatch } from '../../store';
import type { TradeDraft, ValuationDraft } from '../../api/types';
import type { LedgerModule, HoldingSortField, SortOrder } from '../../domain/ledger/constants';
import type { LedgerQuerySnapshot, ProductScope } from '../../domain/ledger/LedgerQueryState';
import type { ValidationResult } from '../../domain/ledger/TradeDraftValidator';
import QueryInputValidator from '../../domain/ledger/QueryInputValidator';
import HoldingsPanel from '../../components/InvestmentLedger/HoldingsPanel';
import LedgerPagination from '../../components/InvestmentLedger/LedgerPagination';
import ModuleSwitch from '../../components/InvestmentLedger/ModuleSwitch';
import PortfolioSummary from '../../components/InvestmentLedger/PortfolioSummary';
import TradeFilterBar from '../../components/InvestmentLedger/TradeFilterBar';
import TradeFormModal from '../../components/InvestmentLedger/TradeFormModal';
import TradeHistoryPanel from '../../components/InvestmentLedger/TradeHistoryPanel';
import ValuationFormModal from '../../components/InvestmentLedger/ValuationFormModal';
import {
  applyQuery,
  changePage,
  changePageSize,
  changeTradeDraft,
  changeValuationDraft,
  closeTradeForm,
  closeValuationForm,
  openHistoryWithScope,
  openTradeForm,
  openValuationForm,
  switchModule,
} from '../../store/ledger/ledgerSlice';
import {
  bootstrapLedger,
  fetchHistory,
  fetchHoldings,
  removeTransaction,
  submitTransaction,
  submitValuation,
} from '../../store/ledger/thunks';
import type { LedgerState } from '../../store/ledger/types';
import styles from './index.module.scss';

/** Redux 映射到页面的只读状态；业务数据均由 ledger slice 持有。 */
interface StateProps {
  readonly activeModule: LedgerState['activeModule'];
  readonly bootstrapping: boolean;
  readonly history: LedgerState['history'];
  readonly holdings: LedgerState['holdings'];
  readonly tradeForm: LedgerState['tradeForm'];
  readonly valuationForm: LedgerState['valuationForm'];
}
/** 注入包含 thunk 能力的应用 dispatch。 */
interface DispatchProps {
  readonly dispatch: AppDispatch;
}

type LedgerPageProps = StateProps & DispatchProps;

/** 从未知拒绝值中提取可直接提示用户的中文消息。 */
const rejectionMessage = (error: unknown, fallback = '网络异常，请稍后重试'): string => {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const value = (error as { readonly message?: unknown }).message;
    if (typeof value === 'string' && value.length > 0) return value;
  }
  return error instanceof Error && error.message.length > 0 ? error.message : fallback;
};

/**
 * 投资交易账本页面容器：负责校验、状态转换、异步用例和用户提示的统一编排。
 * 展示组件只接收数据并上报用户意图，不直接访问通信层。
 */
export class LedgerPage extends React.Component<LedgerPageProps> {
  private readonly queryValidator = new QueryInputValidator();

  public override componentDidMount(): void {
    void this.props.dispatch(bootstrapLedger()).unwrap().catch((error: unknown) => {
      void message.error(rejectionMessage(error, '账本初始化失败，请稍后重试'));
    });
  }

  /** 列表、删除及统计接口失败只提示，不修改或清空当前结果。 */
  public override componentDidUpdate(previousProps: LedgerPageProps): void {
    const { history, holdings } = this.props;
    if (history.error !== null && history.error !== previousProps.history.error) {
      void message.error(history.error);
    }
    if (holdings.error !== null && holdings.error !== previousProps.holdings.error) {
      void message.error(holdings.error);
    }
  }

  /** 显示首条领域校验错误；返回值用于阻止任何后续 dispatch。 */
  private readonly rejectInvalid = (result: ValidationResult, fallback: string): boolean => {
    if (result.valid) return false;
    void message.error(result.fieldErrors[0]?.message ?? fallback);
    return true;
  };

  /** 根据模块加载其当前已应用查询；调用前同步 action 已完成默认状态切换。 */
  private readonly loadModule = (module: LedgerModule): void => {
    if (module === 'history') {
      void this.props.dispatch(fetchHistory());
    } else {
      void this.props.dispatch(fetchHoldings());
    }
  };

  /** 模块导航始终先重置目标模块，再请求其默认浏览结果（需求 2.13、2.14）。 */
  private readonly handleModuleSwitch = (module: LedgerModule): void => {
    if (module === this.props.activeModule) return;
    this.props.dispatch(switchModule(module));
    this.loadModule(module);
  };

  /** 从持仓条目进入历史时仅携带产品范围，其余条件全部恢复默认（需求 2.8、2.9）。 */
  private readonly handleViewTransactions = (scope: ProductScope): void => {
    this.props.dispatch(openHistoryWithScope(scope));
    void this.props.dispatch(fetchHistory());
  };

  /** 校验查询补丁中会导致需求级拒绝的搜索值与日期范围。 */
  private validateQueryPatch(
    query: LedgerQuerySnapshot,
    patch: Partial<LedgerQuerySnapshot>,
  ): boolean {
    for (const value of [patch.productName, patch.productCode]) {
      if (value !== undefined && value !== null
        && this.rejectInvalid(this.queryValidator.validateSearchValue(value), '搜索值无效')) {
        return false;
      }
    }

    if (patch.startDate !== undefined || patch.endDate !== undefined) {
      const startDate = patch.startDate === undefined ? query.startDate : patch.startDate;
      const endDate = patch.endDate === undefined ? query.endDate : patch.endDate;
      if (this.rejectInvalid(
        this.queryValidator.validateDateRange(startDate, endDate),
        '交易日期范围无效',
      )) return false;
    }
    return true;
  }
  /** 仅当补丁有效时更新查询；状态层负责把页码重置为 1。 */
  private readonly handleApplyQuery = (patch: Partial<LedgerQuerySnapshot>): void => {
    const module = this.props.activeModule;
    if (module === null) return;
    const query = module === 'history' ? this.props.history.query : this.props.holdings.query;
    if (!this.validateQueryPatch(query, patch)) return;

    this.props.dispatch(applyQuery({ module, patch }));
    this.loadModule(module);
  };

  /** 清除产品范围等同直接进入历史模块，以默认状态展示全部交易。 */
  private readonly handleClearScope = (): void => {
    this.props.dispatch(switchModule('history'));
    void this.props.dispatch(fetchHistory());
  };

  private readonly handleHistorySort = (order: SortOrder | null): void => {
    this.handleApplyQuery({ tradeDateOrder: order });
  };

  private readonly handleHoldingsSort = (
    field: HoldingSortField | null,
    order: SortOrder | null,
  ): void => {
    this.handleApplyQuery({ holdingSortField: field, holdingSortOrder: order });
  };

  /** 页码无效时仅提示，不派发 changePage，因而保留当前有效结果。 */
  private readonly handlePageChange = (page: number): void => {
    const module = this.props.activeModule;
    if (module === null) return;
    const pageCount = module === 'history'
      ? this.props.history.pageCount
      : this.props.holdings.pageCount;
    if (this.rejectInvalid(
      this.queryValidator.validatePage(page, pageCount),
      '请求的页码无效',
    )) return;

    this.props.dispatch(changePage({ module, page }));
    this.loadModule(module);
  };

  /** 页大小无效时不改变 query 或当前结果；有效时从第 1 页重新请求。 */
  private readonly handlePageSizeChange = (size: number): void => {
    const module = this.props.activeModule;
    if (module === null) return;
    if (this.rejectInvalid(
      this.queryValidator.validatePageSize(size),
      '自定义页大小无效',
    )) return;

    this.props.dispatch(changePageSize({ module, size }));
    this.loadModule(module);
  };

  private readonly handleDelete = (transactionId: number): void => {
    void this.props.dispatch(removeTransaction(transactionId));
  };

  /** 表单 thunk 的校验/API 失败统一由容器 message 提示，字段错误仍留在表单中。 */
  private readonly handleTradeSubmit = (draft: TradeDraft): void => {
    void this.props.dispatch(submitTransaction(draft)).unwrap()
      .then(() => message.success('交易记录已创建'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '交易记录创建失败')));
  };

  private readonly handleValuationSubmit = (draft: ValuationDraft): void => {
    void this.props.dispatch(submitValuation(draft)).unwrap()
      .then(() => message.success('估值记录已保存'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '估值记录保存失败')));
  };

  /** 持仓模块的写意图只提示，不派发任何写 action（需求 1.6、1.7）。 */
  private readonly handleReadOnlyIntent = (kind: 'trade' | 'holding'): void => {
    const content = kind === 'trade'
      ? '请在历史交易记录模块中维护历史交易'
      : '持仓模块仅供查看';
    void message.info(content);
  };

  /** 当前模块的筛选、面板、摘要与分页编排。 */
  private renderActiveModule(module: LedgerModule): React.ReactNode {
    const source = module === 'history' ? this.props.history : this.props.holdings;
    const historyScope: ProductScope | null = this.props.history.query.scopeProductType !== null
      && this.props.history.query.scopeProductCode !== null
      ? {
          productType: this.props.history.query.scopeProductType,
          productCode: this.props.history.query.scopeProductCode,
        }
      : null;

    return (
      <>
        <TradeFilterBar
          query={source.query}
          module={module}
          onApply={this.handleApplyQuery}
          onClearScope={this.handleClearScope}
        />
        {module === 'holdings' ? (
          <>
            <PortfolioSummary
              portfolio={this.props.holdings.portfolio}
              loading={this.props.holdings.loading}
            />
            <HoldingsPanel
              items={this.props.holdings.items}
              loading={this.props.holdings.loading}
              sortField={this.props.holdings.query.holdingSortField}
              sortOrder={this.props.holdings.query.holdingSortOrder}
              onSortChange={this.handleHoldingsSort}
              onViewTransactions={this.handleViewTransactions}
              onReadOnlyIntent={this.handleReadOnlyIntent}
            />
          </>
        ) : (
          <TradeHistoryPanel
            items={this.props.history.items}
            loading={this.props.history.loading}
            tradeDateOrder={this.props.history.query.tradeDateOrder}
            scope={historyScope}
            onSortChange={this.handleHistorySort}
            onDelete={this.handleDelete}
          />
        )}
        <LedgerPagination
          page={source.page}
          pageSize={source.pageSize}
          pageCount={source.pageCount}
          total={source.total}
          onPageChange={this.handlePageChange}
          onPageSizeChange={this.handlePageSizeChange}
        />
      </>
    );
  }

  /** 历史模块是交易维护的唯一入口；持仓模块只提供估值维护与只读浏览。 */
  private renderActions(module: LedgerModule | null): React.ReactNode {
    return (
      <div className={styles.actions}>
        {module === 'history' && (
          <Button type="primary" onClick={() => this.props.dispatch(openTradeForm())}>
            新建交易
          </Button>
        )}
        <Button onClick={() => this.props.dispatch(openValuationForm())}>
          维护估值
        </Button>
      </div>
    );
  }

  public override render(): React.ReactNode {
    const { activeModule, bootstrapping, tradeForm, valuationForm } = this.props;
    return (
      <main className={styles.page}>
        <header className={styles.header}>
          <h1 className={styles.title}>投资交易账本</h1>
          {this.renderActions(activeModule)}
        </header>

        {activeModule === null ? (
          <section className={styles.loading} aria-label="账本加载中">
            <Skeleton active={bootstrapping} />
          </section>
        ) : (
          <>
            <ModuleSwitch
              activeModule={activeModule}
              onSwitch={this.handleModuleSwitch}
            />
            <section className={styles.content} aria-label="账本内容">
              {this.renderActiveModule(activeModule)}
            </section>
          </>
        )}

        <TradeFormModal
          visible={tradeForm.visible}
          draft={tradeForm.draft}
          fieldErrors={tradeForm.fieldErrors}
          submitting={tradeForm.submitting}
          onChange={(patch) => this.props.dispatch(changeTradeDraft(patch))}
          onSubmit={this.handleTradeSubmit}
          onCancel={() => this.props.dispatch(closeTradeForm())}
        />
        <ValuationFormModal
          visible={valuationForm.visible}
          draft={valuationForm.draft}
          fieldErrors={valuationForm.fieldErrors}
          submitting={valuationForm.submitting}
          onChange={(patch) => this.props.dispatch(changeValuationDraft(patch))}
          onSubmit={this.handleValuationSubmit}
          onCancel={() => this.props.dispatch(closeValuationForm())}
        />
      </main>
    );
  }
}

/** 显式约束根状态到容器 props 的映射，避免页面直接读取其它业务分支。 */
const mapStateToProps = (state: RootState): StateProps => ({
  activeModule: state.ledger.activeModule,
  bootstrapping: state.ledger.bootstrapping,
  history: state.ledger.history,
  holdings: state.ledger.holdings,
  tradeForm: state.ledger.tradeForm,
  valuationForm: state.ledger.valuationForm,
});

/** 以 AppDispatch 注入 thunk 派发能力，而不是退化为普通 Dispatch。 */
const mapDispatchToProps = (dispatch: AppDispatch): DispatchProps => ({ dispatch });

/** 类型化容器；页面无路由 own props。 */
export default connect<StateProps, DispatchProps, {}, RootState>(
  mapStateToProps,
  mapDispatchToProps,
)(LedgerPage);
