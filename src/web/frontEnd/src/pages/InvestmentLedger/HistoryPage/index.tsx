import React from 'react';
import { Button, message } from 'antd';
import { connect } from 'react-redux';
import { useLocation } from 'react-router-dom';
import type { Location, NavigateFunction } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import type { RootState, AppDispatch } from '../../../store';
import type { TradeDraft, TransactionOut } from '../../../api/types';
import type { LedgerQuerySnapshot, ProductScope } from '../../../domain/ledger/LedgerQueryState';
import type { SortOrder } from '../../../domain/ledger/constants';
import QueryInputValidator from '../../../domain/ledger/QueryInputValidator';
import TradeFilterBar from '../../../components/InvestmentLedger/TradeFilterBar';
import TradeFormModal from '../../../components/InvestmentLedger/TradeFormModal';
import LedgerPagination from '../../../components/InvestmentLedger/LedgerPagination';
import TradeHistoryPanel from '../../../components/InvestmentLedger/TradeHistoryPanel';
import {
  applyQuery,
  changePage,
  changePageSize,
  changeTradeDraft,
  closeTradeForm,
  openTradeForm,
  openHistoryScope,
  resetHistory,
} from '../../../store/ledger/ledgerSlice';
import {
  fetchHistory,
  removeTransaction,
  submitTransaction,
} from '../../../store/ledger/thunks';
import type { LedgerState } from '../../../store/ledger/types';
import {
  rejectionMessage,
  rejectInvalidPageInput,
  type LedgerNavigationState,
  validateQueryPatch,
} from '../pageUtils';
import styles from '../index.module.scss';

interface StateProps {
  readonly history: LedgerState['history'];
  readonly tradeForm: LedgerState['tradeForm'];
}
interface DispatchProps {
  readonly dispatch: AppDispatch;
}
interface OwnProps {
  readonly navigation: LedgerNavigationState;
  readonly navigate: NavigateFunction;
}
type HistoryPageProps = StateProps & DispatchProps & OwnProps;

/** 历史子路由容器：处理范围/深链初始化、交易查询及唯一的交易写入入口。 */
export class HistoryPageContainer extends React.Component<HistoryPageProps> {
  private readonly queryValidator = new QueryInputValidator();

  public override componentDidMount(): void {
    const { navigation } = this.props;
    if (navigation?.ledgerNavigation === 'holding-scope') {
      this.props.dispatch(openHistoryScope(navigation.scope));
    } else if (navigation?.ledgerNavigation !== 'module-switch') {
      this.props.dispatch(resetHistory());
    }
    void this.props.dispatch(fetchHistory());
  }

  public override componentDidUpdate(previousProps: HistoryPageProps): void {
    if (this.props.history.error !== null
      && this.props.history.error !== previousProps.history.error) {
      void message.error(this.props.history.error);
    }
  }

  private readonly load = (): void => {
    void this.props.dispatch(fetchHistory());
  };

  private readonly handleApplyQuery = (patch: Partial<LedgerQuerySnapshot>): void => {
    if (!validateQueryPatch(this.props.history.query, patch)) return;
    this.props.dispatch(applyQuery({ module: 'history', patch }));
    this.load();
  };

  private readonly handleSort = (order: SortOrder | null): void => {
    this.handleApplyQuery({ tradeDateOrder: order });
  };

  private readonly handleClearScope = (): void => {
    this.props.dispatch(resetHistory());
    this.props.navigate('/investmentLedger/history', {
      replace: true,
      state: { ledgerNavigation: 'module-switch' },
    });
    this.load();
  };

  private readonly handlePageChange = (page: number): void => {
    const result = this.queryValidator.validatePage(page, this.props.history.pageCount);
    if (rejectInvalidPageInput(
      !result.valid,
      result.fieldErrors[0]?.message ?? '请求的页码无效',
    )) return;
    this.props.dispatch(changePage({ module: 'history', page }));
    this.load();
  };

  private readonly handlePageSizeChange = (size: number): void => {
    const result = this.queryValidator.validatePageSize(size);
    if (rejectInvalidPageInput(
      !result.valid,
      result.fieldErrors[0]?.message ?? '自定义页大小无效',
    )) return;
    this.props.dispatch(changePageSize({ module: 'history', size }));
    this.load();
  };

  private readonly handleDelete = (transactionId: number): void => {
    void this.props.dispatch(removeTransaction(transactionId));
  };

  private readonly handleTradeSubmit = (draft: TradeDraft): void => {
    void this.props.dispatch(submitTransaction(draft)).unwrap()
      .then(() => message.success('交易记录已创建'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '交易记录创建失败')));
  };

  public override render(): React.ReactNode {
    const { history, tradeForm } = this.props;
    const scope: ProductScope | null = history.query.scopeProductType !== null
      && history.query.scopeProductCode !== null
      ? {
          productType: history.query.scopeProductType,
          productCode: history.query.scopeProductCode,
        }
      : null;

    return (
      <div className={styles.modulePage}>
        <div className={styles.moduleHeader}>
          <h2 className={styles.moduleTitle}>历史交易记录</h2>
          <Button type="primary" onClick={() => this.props.dispatch(openTradeForm())}>
            新建交易
          </Button>
        </div>
        <TradeFilterBar
          query={history.query}
          module="history"
          onApply={this.handleApplyQuery}
          onClearScope={this.handleClearScope}
        />
        <TradeHistoryPanel
          items={history.items as TransactionOut[]}
          loading={history.loading}
          tradeDateOrder={history.query.tradeDateOrder}
          scope={scope}
          onSortChange={this.handleSort}
          onDelete={this.handleDelete}
        />
        <LedgerPagination
          page={history.page}
          pageSize={history.pageSize}
          pageCount={history.pageCount}
          total={history.total}
          onPageChange={this.handlePageChange}
          onPageSizeChange={this.handlePageSizeChange}
        />
        <TradeFormModal
          visible={tradeForm.visible}
          draft={tradeForm.draft}
          fieldErrors={tradeForm.fieldErrors}
          submitting={tradeForm.submitting}
          onChange={(patch) => this.props.dispatch(changeTradeDraft(patch))}
          onSubmit={this.handleTradeSubmit}
          onCancel={() => this.props.dispatch(closeTradeForm())}
        />
      </div>
    );
  }
}

const mapStateToProps = (state: RootState): StateProps => ({
  history: state.ledger.history,
  tradeForm: state.ledger.tradeForm,
});
const mapDispatchToProps = (dispatch: AppDispatch): DispatchProps => ({ dispatch });
const ConnectedHistoryPage = connect<StateProps, DispatchProps, OwnProps, RootState>(
  mapStateToProps,
  mapDispatchToProps,
)(HistoryPageContainer);

/** 从路由 state 注入导航意图；普通深链没有 state，按默认历史状态处理。 */
const HistoryPage: React.FC = () => {
  const location = useLocation() as Location & { state: LedgerNavigationState };
  const navigate = useNavigate();
  return <ConnectedHistoryPage navigation={location.state ?? null} navigate={navigate} />;
};

export default HistoryPage;
