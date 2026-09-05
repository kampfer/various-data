import React from 'react';
import { Tooltip } from 'antd';
import type { Metric } from '../../../api/types';
import { formatDecimalScale } from '../../../domain/ledger/formatNumbers';
import styles from './index.module.scss';

/** 单个统计指标展示组件的输入契约（需求 3.9）。 */
export interface MetricValueProps {
  /** 待展示指标；不可用时 value 必须为 null。 */
  readonly metric: Metric;
  /** 展示单位，仅追加后缀，不执行浮点换算；quantity 为持仓量，不追加单位。 */
  readonly kind: 'amount' | 'rate' | 'quantity';
}

/** 统一呈现可用与不可用统计指标，避免调用方以 0 代替缺失值。 */
export default class MetricValue extends React.Component<MetricValueProps> {
  /** 不可用原因缺失时使用的中文兜底说明。 */
  private readonly unavailableReason = (): string =>
    this.props.metric.unavailableReason ?? '指标所需数据不完整';

  /** 渲染统计值；金额、比率仅附加展示单位，持仓量保持原始精度不追加后缀。 */
  public override render(): React.ReactNode {
    const { metric, kind } = this.props;
    if (!metric.available) {
      const reason = this.unavailableReason();
      return (
        <Tooltip title={reason}>
          <span className={styles.unavailable} tabIndex={0} aria-label={`不可用：${reason}`}>
            不可用
          </span>
        </Tooltip>
      );
    }

    const rawValue = metric.value ?? '--';
    const value = kind === 'amount' || kind === 'rate'
      ? formatDecimalScale(rawValue, 2)
      : rawValue;
    const suffix = kind === 'amount' ? '元' : kind === 'rate' ? '%' : '';
    return (
      <span className={styles.value}>
        {value}
        {suffix ? ` ${suffix}` : ''}
      </span>
    );
  }
}
