import React from 'react';
import { Button, Table, message } from 'antd';
import type { TableProps } from 'antd';
import type { HoldingOut } from '../../../api/types';
import { PAGE_SIZE_OPTIONS } from '../../../domain/ledger/constants';
import type { HoldingSortField, SortOrder } from '../../../domain/ledger/constants';
import type { ProductScope } from '../../../domain/ledger/LedgerQueryState';
import {
  PRODUCT_TYPE_LABELS,
  formatAccountDisplayName,
} from '../../../domain/ledger/labels';
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
  /** 当前页码，1 起；未提供时表格不启用分页。 */
  readonly page?: number;
  /** 当前页大小；未提供时表格不启用分页。 */
  readonly pageSize?: number;
  /** 分页前结果总数；未提供时表格不启用分页。 */
  readonly total?: number;
  /** 翻页回调。 */
  readonly onPageChange?: (page: number) => void;
  /** 页大小变更回调；redux 会负责把页码重置为 1。 */
  readonly onPageSizeChange?: (size: number) => void;
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
  /** 表格 onChange 同时承接分页与排序；页大小变化优先，其次翻页，最后排序。 */
  private readonly handleTableChange: TableChangeHandler = (
    pagination,
    _filters,
    sorter,
  ): void => {
    const nextPageSize = pagination.pageSize;
    const nextPage = pagination.current;
    if (
      typeof this.props.pageSize === 'number'
      && typeof nextPageSize === 'number'
      && nextPageSize !== this.props.pageSize
    ) {
      this.props.onPageSizeChange?.(nextPageSize);
      return;
    }
    if (
      typeof this.props.page === 'number'
      && typeof nextPage === 'number'
      && nextPage !== this.props.page
    ) {
      this.props.onPageChange?.(nextPage);
      return;
    }

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

  /** 生成持仓汇总列；产品名称本身作为进入历史交易的导航入口。 */
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
              productCode: record.productCode,
              productName: value,
            })}
          >
            {value}
          </Button>
        ),
      },
      { title: '产品代码', dataIndex: 'productCode', key: 'productCode' },
      {
        title: '交易账户',
        dataIndex: 'accounts',
        key: 'accounts',
        render: (_accounts: HoldingOut['accounts'], record: HoldingOut) => {
          const labels = (record.accounts ?? []).map(
            (account) => formatAccountDisplayName(
              account.accountInstitution,
              account.accountName,
            ) ?? '未关联账户',
          );
          return labels.length > 0 ? labels.join('、') : '未关联账户';
        },
      },
      {
        title: '持仓量',
        dataIndex: 'positionQuantity',
        key: 'positionQuantity',
        render: (metric: HoldingOut['positionQuantity']) => <MetricValue metric={metric} kind="quantity" />,
      },
      {
        title: '持仓额',
        dataIndex: 'position',
        key: 'position',
        sorter: true,
        sortOrder: this.sortOrderFor('position'),
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

  /** 根据传入的分页 props 构造 antd Table 分页配置；缺少任一字段则禁用分页。 */
  private renderPagination(): false | NonNullable<TableProps<HoldingOut>['pagination']> {
    const { page, pageSize, total } = this.props;
    if (typeof page !== 'number' || typeof pageSize !== 'number' || typeof total !== 'number') {
      return false;
    }
    const pageCount = pageSize > 0 ? Math.ceil(total / pageSize) : 0;
    return {
      current: page,
      pageSize,
      total,
      showSizeChanger: true,
      pageSizeOptions: PAGE_SIZE_OPTIONS.map(String),
      showTotal: () => `第 ${page} 页 / 共 ${pageCount} 页`,
    };
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
            pagination={this.renderPagination()}
            rowKey={(record) => `${record.productType}:${record.productCode}`}
            onChange={this.handleTableChange}
          />
        </div>
      </section>
    );
  }
}
