import React from 'react';
import { Descriptions, Skeleton } from 'antd';
import type { PortfolioStatisticsOut } from '../../../api/types';
import MetricValue from '../MetricValue';
import styles from './index.module.scss';

/** 投资组合统计摘要属性（需求 3.10-3.12）。 */
export interface PortfolioSummaryProps {
  /** 组合统计；null 表示尚未取得，不能以 0 代替。 */
  readonly portfolio: PortfolioStatisticsOut | null;
  /** 组合统计加载状态。 */
  readonly loading: boolean;
}

/** 以统一指标组件只读展示投资组合的四项统计。 */
export default class PortfolioSummary extends React.Component<PortfolioSummaryProps> {
  public override render(): React.ReactNode {
    const { portfolio, loading } = this.props;
    return (
      <section className={styles.summary} aria-label="投资组合统计">
        {portfolio === null ? (
          <Skeleton active={loading} paragraph={{ rows: 1 }} />
        ) : (
          <Descriptions bordered column={4} size="small">
            <Descriptions.Item label="总持仓">
              <MetricValue metric={portfolio.totalPosition} kind="amount" />
            </Descriptions.Item>
            <Descriptions.Item label="总收益">
              <MetricValue metric={portfolio.totalProfit} kind="amount" />
            </Descriptions.Item>
            <Descriptions.Item label="总收益率">
              <MetricValue metric={portfolio.totalProfitRate} kind="rate" />
            </Descriptions.Item>
            <Descriptions.Item label="总年化收益率">
              <MetricValue metric={portfolio.totalAnnualizedRate} kind="rate" />
            </Descriptions.Item>
          </Descriptions>
        )}
      </section>
    );
  }
}
