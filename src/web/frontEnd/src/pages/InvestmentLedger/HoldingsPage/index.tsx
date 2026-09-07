import React from 'react';
import { message } from 'antd';
import { connect } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import type { NavigateFunction } from 'react-router-dom';
import type { RootState, AppDispatch } from '../../../store';
import HoldingsPanel from '../../../components/InvestmentLedger/HoldingsPanel';
import { fetchHoldings } from '../../../store/ledger/thunks';
import type { LedgerState } from '../../../store/ledger/types';
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
  public override componentDidMount(): void {
    void this.props.dispatch(fetchHoldings());
  }

  public override componentDidUpdate(previousProps: HoldingsPageProps): void {
    if (this.props.holdings.error !== null
      && this.props.holdings.error !== previousProps.holdings.error) {
      void message.error(this.props.holdings.error);
    }
  }

  /** 产品名称点击后携带产品范围跳转到历史交易模块。 */
  private readonly handleViewTransactions = (scope: {
    readonly productCode: string;
    readonly productName: string;
  }): void => {
    const params = new URLSearchParams({
      productCode: scope.productCode,
      productName: scope.productName,
    });
    this.props.navigate(`/investmentLedger/history?${params.toString()}`);
  };

  public override render(): React.ReactNode {
    const { holdings } = this.props;
    return (
      <div className={styles.modulePage}>
        <HoldingsPanel
          items={holdings.items}
          loading={holdings.loading}
          onViewTransactions={this.handleViewTransactions}
          onReadOnlyIntent={() => message.info('持仓模块仅供查看')}
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
