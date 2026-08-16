import React from 'react';
import { message } from 'antd';
import { connect } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import type { NavigateFunction } from 'react-router-dom';
import type { RootState, AppDispatch } from '../../../store';
import type { LedgerQuerySnapshot } from '../../../domain/ledger/LedgerQueryState';
import type { HoldingSortField, SortOrder } from '../../../domain/ledger/constants';
import QueryInputValidator from '../../../domain/ledger/QueryInputValidator';
import HoldingsPanel from '../../../components/InvestmentLedger/HoldingsPanel';
import LedgerPagination from '../../../components/InvestmentLedger/LedgerPagination';
import PortfolioSummary from '../../../components/InvestmentLedger/PortfolioSummary';
import TradeFilterBar from '../../../components/InvestmentLedger/TradeFilterBar';
import { applyQuery, changePage, changePageSize } from '../../../store/ledger/ledgerSlice';
import { fetchHoldings } from '../../../store/ledger/thunks';
import type { LedgerState } from '../../../store/ledger/types';
import { rejectionMessage, rejectInvalidPageInput, validateQueryPatch } from '../pageUtils';
import styles from '../index.module.scss';

interface StateProps {
  readonly holdings: LedgerState['holdings'];
}
interface DispatchProps {
  readonly dispatch: AppDispatch;
}
interface OwnProps {
  readonly navigate: NavigateFunction;
}
type HoldingsPageProps = StateProps & DispatchProps & OwnProps;

/** 持仓子路由容器：只查询当前持仓快照，并把历史入口转换为 holding-scope 导航。 */
export class HoldingsPageContainer extends React.Component<HoldingsPageProps> {
  private readonly queryValidator = new QueryInputValidator();

  public override componentDidMount(): void {
    void this.props.dispatch(fetchHoldings());
  }

  public override componentDidUpdate(previousProps: HoldingsPageProps): void {
    if (this.props.holdings.error !== null
      && this.props.holdings.error !== previousProps.holdings.error) {
      void message.error(this.props.holdings.error);
    }
  }

  private readonly load = (): void => {
    void this.props.dispatch(fetchHoldings());
  };

  private readonly handleApplyQuery = (patch: Partial<LedgerQuerySnapshot>): void => {
    if (!validateQueryPatch(this.props.holdings.query, patch)) return;
    this.props.dispatch(applyQuery({ module: 'holdings', patch }));
    this.load();
  };

  private readonly handleSort = (
    field: HoldingSortField | null,
    order: SortOrder | null,
  ): void => {
    this.handleApplyQuery({ holdingSortField: field, holdingSortOrder: order });
  };

  private readonly handleViewTransactions = (scope: {
    readonly productType: 'WEALTH' | 'FUND' | 'STOCK';
    readonly productCode: string;
  }): void => {
    this.props.navigate('/investmentLedger/history', {
      state: { ledgerNavigation: 'holding-scope', scope },
    });
  };

  private readonly handlePageChange = (page: number): void => {
    const result = this.queryValidator.validatePage(page, this.props.holdings.pageCount);
    if (rejectInvalidPageInput(
      !result.valid,
      result.fieldErrors[0]?.message ?? '请求的页码无效',
    )) return;
    this.props.dispatch(changePage({ module: 'holdings', page }));
    this.load();
  };

  private readonly handlePageSizeChange = (size: number): void => {
    const result = this.queryValidator.validatePageSize(size);
    if (rejectInvalidPageInput(
      !result.valid,
      result.fieldErrors[0]?.message ?? '自定义页大小无效',
    )) return;
    this.props.dispatch(changePageSize({ module: 'holdings', size }));
    this.load();
  };

  public override render(): React.ReactNode {
    const { holdings } = this.props;
    return (
      <div className={styles.modulePage}>
        <TradeFilterBar
          query={holdings.query}
          module="holdings"
          onApply={this.handleApplyQuery}
          onClearScope={() => undefined}
        />
        <PortfolioSummary portfolio={holdings.portfolio} loading={holdings.loading} />
        <HoldingsPanel
          items={holdings.items}
          loading={holdings.loading}
          sortField={holdings.query.holdingSortField}
          sortOrder={holdings.query.holdingSortOrder}
          onSortChange={this.handleSort}
          onViewTransactions={this.handleViewTransactions}
          onReadOnlyIntent={() => message.info('持仓模块仅供查看')}
        />
        <LedgerPagination
          page={holdings.page}
          pageSize={holdings.pageSize}
          pageCount={holdings.pageCount}
          total={holdings.total}
          onPageChange={this.handlePageChange}
          onPageSizeChange={this.handlePageSizeChange}
        />
      </div>
    );
  }
}

const mapStateToProps = (state: RootState): StateProps => ({ holdings: state.ledger.holdings });
const mapDispatchToProps = (dispatch: AppDispatch): DispatchProps => ({ dispatch });
const ConnectedHoldingsPage = connect<StateProps, DispatchProps, OwnProps, RootState>(
  mapStateToProps,
  mapDispatchToProps,
)(HoldingsPageContainer);

/** 为类容器注入 react-router 的导航能力。 */
const HoldingsPage: React.FC = () => {
  const navigate = useNavigate();
  return <ConnectedHoldingsPage navigate={navigate} />;
};

export default HoldingsPage;
