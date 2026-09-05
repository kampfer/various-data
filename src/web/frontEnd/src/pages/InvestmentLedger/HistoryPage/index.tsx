import React from 'react';
import { Button, message } from 'antd';
import { connect } from 'react-redux';
import { useLocation, useSearchParams } from 'react-router-dom';
import type { Location, NavigateFunction } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import type { RootState, AppDispatch } from '../../../store';
import type { TradeDraft, TransactionOut } from '../../../api/types';
import type { LedgerQuerySnapshot } from '../../../domain/ledger/LedgerQueryState';
import type { SortOrder } from '../../../domain/ledger/constants';
import TradeFilterBar from '../../../components/InvestmentLedger/TradeFilterBar';
import TradeFormModal from '../../../components/InvestmentLedger/TradeFormModal';
import FundTradeFormModal from '../../../components/InvestmentLedger/FundTradeFormModal';
import TradeHistoryPanel from '../../../components/InvestmentLedger/TradeHistoryPanel';
import {
  applyQuery,
  changePage,
  changePageSize,
  changeTradeDraft,
  closeTradeForm,
  openTradeForm,
  openFundTradeForm,
  openHistoryScope,
  resetHistory,
} from '../../../store/ledger/ledgerSlice';
import {
  fetchAccounts,
  fetchHistory,
  removeTransaction,
  submitTransaction,
} from '../../../store/ledger/thunks';
import type { LedgerState } from '../../../store/ledger/types';
import {
  rejectionMessage,
  type LedgerNavigationState,
  validateQueryPatch,
} from '../pageUtils';
import styles from '../index.module.scss';

interface StateProps {
  readonly history: LedgerState['history'];
  readonly tradeForm: LedgerState['tradeForm'];
  readonly accounts: LedgerState['accounts'];
}
interface DispatchProps {
  readonly dispatch: AppDispatch;
}
interface OwnProps {
  readonly navigation: LedgerNavigationState;
  readonly navigate: NavigateFunction;
  /** URL 查询参数中的产品代码；非空表示进入产品历史交易范围。 */
  readonly scopeProductCode: string | null;
  /** URL 查询参数中的产品名称；仅供页面标题展示。 */
  readonly scopeProductName: string | null;
}
type HistoryPageProps = StateProps & DispatchProps & OwnProps;

/** 历史子路由容器：处理范围/深链初始化、交易查询及唯一的交易写入入口。 */
export class HistoryPageContainer extends React.Component<HistoryPageProps> {
  public override componentDidMount(): void {
    this.syncScopeFromUrl();
    void this.props.dispatch(fetchAccounts());
    void this.props.dispatch(fetchHistory());
  }

  public override componentDidUpdate(previousProps: HistoryPageProps): void {
    if (this.props.history.error !== null
      && this.props.history.error !== previousProps.history.error) {
      void message.error(this.props.history.error);
    }
    if (this.props.accounts.error !== null
      && this.props.accounts.error !== previousProps.accounts.error) {
      void message.error(this.props.accounts.error);
    }
    // URL 中的产品代码变化时重新同步范围并刷新
    if (this.props.scopeProductCode !== previousProps.scopeProductCode) {
      this.syncScopeFromUrl();
      void this.props.dispatch(fetchHistory());
    }
  }

  /** 根据 URL 中的 productCode 同步 redux 中的范围状态。 */
  private readonly syncScopeFromUrl = (): void => {
    const { scopeProductCode, scopeProductName, navigation } = this.props;
    if (scopeProductCode !== null) {
      this.props.dispatch(openHistoryScope({
        productCode: scopeProductCode,
        productName: scopeProductName ?? '',
      }));
      return;
    }
    // URL 无范围参数时：非模块切换或 redux 中残留旧范围都需要重置
    const hasStaleScope = this.props.history.query.scopeProductCode !== null;
    if (navigation?.ledgerNavigation !== 'module-switch' || hasStaleScope) {
      this.props.dispatch(resetHistory());
    }
  };

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

  /** 退出产品范围：导航到无参数的历史路由，componentDidUpdate 会自动同步并刷新。 */
  private readonly handleClearScope = (): void => {
    this.props.navigate('/investmentLedger/history', { replace: true });
  };

  /** antd Table 内置分页已约束页码有效，直接派发并重新拉取。 */
  private readonly handlePageChange = (page: number): void => {
    this.props.dispatch(changePage({ module: 'history', page }));
    this.load();
  };

  /** 切换页大小由 redux 把页码重置为 1，再重新拉取。 */
  private readonly handlePageSizeChange = (size: number): void => {
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
    const { history, tradeForm, accounts, scopeProductCode, scopeProductName } = this.props;
    const scoped = scopeProductCode !== null;

    return (
      <div className={styles.modulePage}>
        <div className={styles.moduleHeader}>
          <h2 className={styles.moduleTitle}>
            {scoped ? `${scopeProductName ?? scopeProductCode} - 历史交易` : '历史交易记录'}
          </h2>
          {scoped && (
            <Button onClick={this.handleClearScope}>返回全部交易</Button>
          )}
          <div className={styles.headerActions}>
            {/* <Button type="primary" onClick={() => this.props.dispatch(openTradeForm())}>
              新建交易
            </Button> */}
            <Button type="primary" onClick={() => this.props.dispatch(openFundTradeForm())}>
              新建基金交易
            </Button>
          </div>
        </div>
        <TradeFilterBar
          query={history.query}
          module="history"
          scoped={scoped}
          onApply={this.handleApplyQuery}
        />
        <TradeHistoryPanel
          items={history.items as TransactionOut[]}
          loading={history.loading}
          tradeDateOrder={history.query.tradeDateOrder}
          onSortChange={this.handleSort}
          onDelete={this.handleDelete}
          page={history.page}
          pageSize={history.pageSize}
          total={history.total}
          onPageChange={this.handlePageChange}
          onPageSizeChange={this.handlePageSizeChange}
        />
        <TradeFormModal
          visible={tradeForm.visible && tradeForm.mode === 'general'}
          draft={tradeForm.draft}
          accounts={accounts.items}
          fieldErrors={tradeForm.fieldErrors}
          submitting={tradeForm.submitting}
          onChange={(patch) => this.props.dispatch(changeTradeDraft(patch))}
          onSubmit={this.handleTradeSubmit}
          onCancel={() => this.props.dispatch(closeTradeForm())}
        />
        <FundTradeFormModal
          visible={tradeForm.visible && tradeForm.mode === 'fund'}
          draft={tradeForm.draft}
          accounts={accounts.items}
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
  accounts: state.ledger.accounts,
});
const mapDispatchToProps = (dispatch: AppDispatch): DispatchProps => ({ dispatch });
const ConnectedHistoryPage = connect<StateProps, DispatchProps, OwnProps, RootState>(
  mapStateToProps,
  mapDispatchToProps,
)(HistoryPageContainer);

/** 从路由 state 注入导航意图；URL 查询参数提供产品历史交易范围。 */
const HistoryPage: React.FC = () => {
  const location = useLocation() as Location & { state: LedgerNavigationState };
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const scopeProductCode = searchParams.get('productCode');
  const scopeProductName = searchParams.get('productName');
  return (
    <ConnectedHistoryPage
      navigation={location.state ?? null}
      navigate={navigate}
      scopeProductCode={scopeProductCode}
      scopeProductName={scopeProductName}
    />
  );
};

export default HistoryPage;
