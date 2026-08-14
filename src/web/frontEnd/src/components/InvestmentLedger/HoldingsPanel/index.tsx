import React from 'react';
import { Button, Table, message } from 'antd';
import type { TableProps } from 'antd';
import type { HoldingOut } from '../../../api/types';
import type { HoldingSortField, SortOrder } from '../../../domain/ledger/constants';
import type { ProductScope } from '../../../domain/ledger/LedgerQueryState';
import { PRODUCT_TYPE_LABELS } from '../../../domain/ledger/labels';
import MetricValue from '../MetricValue';
import styles from './index.module.scss';

type HoldingColumns = NonNullable<TableProps<HoldingOut>['columns']>;
type TableChangeHandler = NonNullable<TableProps<HoldingOut>['onChange']>;
type AntSortOrder = 'ascend' | 'descend' | null;
type ReadOnlyIntent = 'trade' | 'holding';

/** 持仓只读表格属性（需求 1.6、1.7、2.4-2.8、2.19、2.22）。 */
export interface HoldingsPanelProps {
  /** 当前页持仓条目。 */
  readonly items: readonly HoldingOut[];
  /** 表格加载状态。 */
  readonly loading: boolean;
  /** 当前数值排序字段；null 表示按来源顺序。 */
  readonly sortField: HoldingSortField | null;
  /** 当前数值排序方向。 */
  readonly sortOrder: SortOrder | null;
  /** 持仓或总收益排序变化回调。 */
  readonly onSortChange: (field: HoldingSortField | null, order: SortOrder | null) => void;
  /** 进入指定产品的历史交易记录模块。 */
  readonly onViewTransactions: (scope: ProductScope) => void;
  /** 只读意图提示完成后的通知，不承载写请求。 */
  readonly onReadOnlyIntent: (kind: ReadOnlyIntent) => void;
}

/** 仅展示产品级汇总，不持有逐笔数据，也不提供任何写控件。 */
export default class HoldingsPanel extends React.Component<HoldingsPanelProps> {
  /** 将领域排序码转换为 antd 受控排序值。 */
  private sortOrderFor(field: HoldingSortField): AntSortOrder {
    if (this.props.sortField !== field) return null;
    if (this.props.sortOrder === 'asc') return 'ascend';
    if (this.props.sortOrder === 'desc') return 'descend';
    return null;
  }
  /** 表格排序仅允许持仓与总收益，取消排序时恢复来源顺序。 */
  private readonly handleTableChange: TableChangeHandler = (
    _pagination,
    _filters,
    sorter,
  ): void => {
    const activeSorter = Array.isArray(sorter)
      ? sorter.find((item) => item.columnKey === 'position' || item.columnKey === 'totalProfit')
      : sorter;
    const field = activeSorter?.columnKey;
    if (field !== 'position' && field !== 'totalProfit') return;

    const sorterOrder = activeSorter?.order;
    const order: SortOrder | null = sorterOrder === 'ascend'
      ? 'asc'
      : sorterOrder === 'descend'
        ? 'desc'
        : null;
    this.props.onSortChange(order === null ? null : field, order);
  };

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

  /** 生成恰好 7 个只读列；产品名称本身作为进入历史交易的导航入口。 */
  private columns(): HoldingColumns {
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
        render: (value: string, record: HoldingOut) => (
          <Button
            aria-label={`查看${value}的历史交易`}
            className={styles.historyLink}
            type="link"
            onClick={() => this.props.onViewTransactions({
              productType: record.productType,
              productCode: record.productCode,
            })}
          >
            {value}
          </Button>
        ),
      },
      { title: '产品代码', dataIndex: 'productCode', key: 'productCode' },
      {
        title: '持仓',
        dataIndex: 'position',
        key: 'position',
        sorter: true,
        sortOrder: this.sortOrderFor('position'),
        render: (metric: HoldingOut['position']) => <MetricValue metric={metric} kind="amount" />,
      },
      {
        title: '总收益',
        dataIndex: 'totalProfit',
        key: 'totalProfit',
        sorter: true,
        sortOrder: this.sortOrderFor('totalProfit'),
        render: (metric: HoldingOut['totalProfit']) => <MetricValue metric={metric} kind="amount" />,
      },
      {
        title: '总收益率',
        dataIndex: 'totalProfitRate',
        key: 'totalProfitRate',
        render: (metric: HoldingOut['totalProfitRate']) => <MetricValue metric={metric} kind="rate" />,
      },
      {
        title: '年化收益率',
        dataIndex: 'annualizedRate',
        key: 'annualizedRate',
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
            dataSource={this.props.items}
            loading={this.props.loading}
            locale={{ emptyText: '暂无数据' }}
            pagination={false}
            rowKey={(record) => `${record.productType}:${record.productCode}`}
            onChange={this.handleTableChange}
          />
        </div>
      </section>
    );
  }
}
