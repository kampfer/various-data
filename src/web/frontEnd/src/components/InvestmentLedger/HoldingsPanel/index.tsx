import React from 'react';
import { Button, Table, message } from 'antd';
import type { TableProps } from 'antd';
import type { ColumnType } from 'antd/es/table';
import type { HoldingOut, Metric } from '../../../api/types';
import type { ProductScope } from '../../../domain/ledger/LedgerQueryState';
import {
  PRODUCT_TYPE_LABELS,
  formatAccountDisplayName,
} from '../../../domain/ledger/labels';
import MetricValue from '../MetricValue';
import styles from './index.module.scss';

type HoldingColumns = NonNullable<TableProps<HoldingOut>['columns']>;
type ReadOnlyIntent = 'trade' | 'holding';

/** 未关联账户在筛选与展示中的统一文案。 */
const UNLINKED_ACCOUNT_LABEL = '未关联账户';

/** 持仓只读表格属性（需求 1.6、1.7、2.4-2.8、2.22）。 */
export interface HoldingsPanelProps {
  /** 全量持仓条目；表格自身承担筛选与排序，不再依赖后端分页。 */
  readonly items: readonly HoldingOut[];
  /** 表格加载状态。 */
  readonly loading: boolean;
  /** 进入指定产品的历史交易记录模块。 */
  readonly onViewTransactions: (scope: ProductScope) => void;
  /** 只读意图提示完成后的通知，不承载写请求。 */
  readonly onReadOnlyIntent: (kind: ReadOnlyIntent) => void;
}

/** 仅展示产品级汇总，不持有逐笔数据，也不提供任何写控件。 */
export default class HoldingsPanel extends React.Component<HoldingsPanelProps> {
  /**
   * 承接其它入口产生的写意图：只显示信息提示并通知容器，不调用通信层。
   * 该公开方法不对应任何表格写控件，供上层通过组件引用转发意图。
   */
  public readonly notifyReadOnlyIntent = (kind: ReadOnlyIntent): void => {
    const content = kind === 'trade'
      ? '请在历史交易记录模块中维护历史交易'
      : '持仓模块仅供查看';
    void message.info(content);
    this.props.onReadOnlyIntent(kind);
  };

  /** 把 Metric 转成用于排序的数值；不可用或空值统一视为负无穷，稳定排到末尾。 */
  private static metricNumber(metric: Metric): number {
    if (!metric.available || metric.value === null) return Number.NEGATIVE_INFINITY;
    const parsed = Number.parseFloat(metric.value);
    return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
  }

  /** 生成按 Metric 数值升序比较的 sorter；antd 会依据当前方向自动反转。 */
  private static metricSorter(
    field: keyof Pick<
      HoldingOut,
      'positionQuantity' | 'position' | 'totalProfit' | 'totalProfitRate' | 'annualizedRate'
    >,
  ): (a: HoldingOut, b: HoldingOut) => number {
    return (a, b) =>
      HoldingsPanel.metricNumber(a[field]) - HoldingsPanel.metricNumber(b[field]);
  }

  /**
   * 依据当前数据构造去重的文本筛选项。
   * accessor 返回单条记录贡献的一个或多个候选值（如账户可关联多个），
   * 全部去重并按中文排序后作为筛选项。
   */
  private static textFilters(
    items: readonly HoldingOut[],
    accessor: (item: HoldingOut) => string | readonly string[],
  ): ColumnType<HoldingOut>['filters'] {
    const seen = new Set<string>();
    for (const item of items) {
      const values = accessor(item);
      if (typeof values === 'string') {
        seen.add(values);
      } else {
        values.forEach((value) => seen.add(value));
      }
    }
    return Array.from(seen)
      .sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
      .map((value) => ({ text: value, value }));
  }

  /** 把持仓涉及的账户格式化为展示标签数组；无账户回退到未关联文案。 */
  private static accountLabels(record: HoldingOut): string[] {
    const labels = (record.accounts ?? []).map(
      (account) => formatAccountDisplayName(
        account.accountInstitution,
        account.accountName,
      ) ?? UNLINKED_ACCOUNT_LABEL,
    );
    return labels.length > 0 ? labels : [UNLINKED_ACCOUNT_LABEL];
  }

  /**
   * 生成持仓汇总列。
   * - 产品名称本身作为进入历史交易的导航入口；
   * - 产品名称、产品代码、交易账户提供 antd 自带列筛选；
   * - 持仓量、持仓额、总收益、总收益率、年化收益率提供前端排序。
   */
  private columns(): HoldingColumns {
    const { items } = this.props;
    return [
      {
        title: '产品类型',
        dataIndex: 'productType',
        key: 'productType',
        render: (value: HoldingOut['productType']) => PRODUCT_TYPE_LABELS[value],
      },
      {
        title: '产品名称',
        dataIndex: 'productName',
        key: 'productName',
        // 名称列同时承担筛选入口（antd 自带）与历史交易导航
        filters: HoldingsPanel.textFilters(items, (item) => item.productName),
        filterSearch: true,
        onFilter: (value, record) => record.productName === value,
        render: (value: string, record: HoldingOut) => (
          <Button
            aria-label={`查看${value}的历史交易`}
            className={styles.historyLink}
            type="link"
            onClick={() => this.props.onViewTransactions({
              productCode: record.productCode,
              productName: value,
            })}
          >
            {value}
          </Button>
        ),
      },
      {
        title: '产品代码',
        dataIndex: 'productCode',
        key: 'productCode',
        filters: HoldingsPanel.textFilters(items, (item) => item.productCode),
        filterSearch: true,
        onFilter: (value, record) => record.productCode === value,
      },
      {
        title: '交易账户',
        dataIndex: 'accounts',
        key: 'accounts',
        // 一个产品可能关联多个账户，命中任一账户即视为匹配
        filters: HoldingsPanel.textFilters(
          items,
          // 展开每个账户标签作为独立筛选项
          (item) => HoldingsPanel.accountLabels(item),
        ),
        filterSearch: true,
        onFilter: (value, record) =>
          HoldingsPanel.accountLabels(record).includes(String(value)),
        render: (_accounts: HoldingOut['accounts'], record: HoldingOut) =>
          HoldingsPanel.accountLabels(record).join('、'),
      },
      {
        title: '持仓量',
        dataIndex: 'positionQuantity',
        key: 'positionQuantity',
        sorter: HoldingsPanel.metricSorter('positionQuantity'),
        render: (metric: HoldingOut['positionQuantity']) => <MetricValue metric={metric} kind="quantity" />,
      },
      {
        title: '持仓额',
        dataIndex: 'position',
        key: 'position',
        sorter: HoldingsPanel.metricSorter('position'),
        render: (metric: HoldingOut['position']) => <MetricValue metric={metric} kind="amount" />,
      },
      {
        title: '最新净值',
        dataIndex: 'latestValuationUnitPrice',
        key: 'latestValuationUnitPrice',
        render: (metric: HoldingOut['latestValuationUnitPrice']) => (
          <MetricValue metric={metric} kind="quantity" />
        ),
      },
      {
        title: '最新净值日期',
        dataIndex: 'latestValuationDate',
        key: 'latestValuationDate',
        render: (value: HoldingOut['latestValuationDate']) => value ?? '--',
      },
      {
        title: '总收益',
        dataIndex: 'totalProfit',
        key: 'totalProfit',
        sorter: HoldingsPanel.metricSorter('totalProfit'),
        render: (metric: HoldingOut['totalProfit']) => <MetricValue metric={metric} kind="amount" />,
      },
      {
        title: '总收益率',
        dataIndex: 'totalProfitRate',
        key: 'totalProfitRate',
        sorter: HoldingsPanel.metricSorter('totalProfitRate'),
        render: (metric: HoldingOut['totalProfitRate']) => <MetricValue metric={metric} kind="rate" />,
      },
      {
        title: '年化收益率',
        dataIndex: 'annualizedRate',
        key: 'annualizedRate',
        sorter: HoldingsPanel.metricSorter('annualizedRate'),
        render: (metric: HoldingOut['annualizedRate']) => <MetricValue metric={metric} kind="rate" />,
      },
    ];
  }

  public override render(): React.ReactNode {
    return (
      <section className={styles.panel} aria-label="持仓面板">
        <div className={styles.table}>
          <Table<HoldingOut>
            aria-label="持仓表格"
            columns={this.columns()}
            dataSource={this.props.items as HoldingOut[]}
            loading={this.props.loading}
            locale={{ emptyText: '暂无数据' }}
            pagination={false}
            rowKey={(record) => `${record.productType}:${record.productCode}`}
          />
        </div>
      </section>
    );
  }
}
