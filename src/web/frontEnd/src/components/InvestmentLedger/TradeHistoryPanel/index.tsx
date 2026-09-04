import React from 'react';
import { Button, Popconfirm, Table } from 'antd';
import type { TableProps } from 'antd';
import type { TransactionOut } from '../../../api/types';
import { PAGE_SIZE_OPTIONS } from '../../../domain/ledger/constants';
import type { SortOrder } from '../../../domain/ledger/constants';
import {
  PRODUCT_TYPE_LABELS,
  TRADE_DIRECTION_LABELS,
  TRADE_VALUE_LABELS,
  formatAccountDisplayName,
} from '../../../domain/ledger/labels';
import { formatPriceByProductType } from '../../../domain/ledger/formatNumbers';
import computeTransactionAmount from '../../../domain/ledger/transactionAmount';
import styles from './index.module.scss';

type TransactionColumns = NonNullable<TableProps<TransactionOut>['columns']>;
type TableChangeHandler = NonNullable<TableProps<TransactionOut>['onChange']>;

/** 历史交易表格面板属性（需求 1.4、1.5、2.10-2.12、2.15、2.22、2.23）。 */
export interface TradeHistoryPanelProps {
  /** 当前页逐笔交易；相同 id 的重复输入只渲染一次。 */
  readonly items: readonly TransactionOut[];
  /** 表格加载状态。 */
  readonly loading: boolean;
  /** 当前交易日期排序；null 表示未启用。 */
  readonly tradeDateOrder: SortOrder | null;
  /** 交易日期排序变化回调。 */
  readonly onSortChange: (order: SortOrder | null) => void;
  /** 确认删除后的回调；id 不向用户展示。 */
  readonly onDelete: (transactionId: number) => void;
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

/** 只负责历史交易展示与用户意图回调，不请求接口或编辑交易。 */
export default class TradeHistoryPanel extends React.Component<TradeHistoryPanelProps> {
  /** 保持首次出现顺序，并防止同一交易被重复渲染。 */
  private uniqueItems(): TransactionOut[] {
    const seen = new Set<number>();
    return this.props.items.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
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
      ? sorter.find((item) => item.columnKey === 'tradeDate')
      : sorter;
    if (activeSorter?.columnKey !== 'tradeDate') return;

    const order: SortOrder | null = activeSorter.order === 'ascend'
      ? 'asc'
      : activeSorter.order === 'descend'
        ? 'desc'
        : null;
    this.props.onSortChange(order);
  };

  /** 9 个数据列与 1 个删除操作列；不定义 id 或编辑列。 */
  private columns(): TransactionColumns {
    const sortOrder = this.props.tradeDateOrder === 'asc'
      ? 'ascend'
      : this.props.tradeDateOrder === 'desc'
        ? 'descend'
        : null;

    return [
      {
        title: '产品类型',
        dataIndex: 'productType',
        key: 'productType',
        render: (value: TransactionOut['productType']) => PRODUCT_TYPE_LABELS[value],
      },
      { title: '产品名称', dataIndex: 'productName', key: 'productName' },
      { title: '产品代码', dataIndex: 'productCode', key: 'productCode' },
      {
        title: '交易账户',
        dataIndex: 'accountName',
        key: 'accountName',
        render: (value: string | null, record: TransactionOut) =>
          formatAccountDisplayName(record.accountInstitution, value) ?? '未关联账户',
      },
      {
        title: '净值/单价', dataIndex: 'transactionPrice', key: 'transactionPrice',
        // 基金/理财净值固定 4 位小数展示；股票单价保持原样（精度无限制）
        render: (value: string, record: TransactionOut) => formatPriceByProductType(value, record.productType),
      },
      {
        title: '份额/数量', dataIndex: 'transactionQuantity', key: 'transactionQuantity',
        // render: (value: string, record: TransactionOut) => `${TRADE_VALUE_LABELS[record.productType].quantity}：${value}`,
      },
      // 费用：随交易落库，未填写时后端归一为 0（需求 6.2、6.5）
      { title: '费用', dataIndex: 'fee', key: 'fee' },
      // 交易金额：由已落库字段计算展示，不作为独立字段从后端返回（需求 6.5、6.6）
      {
        title: '交易金额',
        key: 'transactionAmount',
        render: (_value: unknown, record: TransactionOut) =>
          computeTransactionAmount(record.transactionPrice, record.transactionQuantity, record.fee),
      },
      {
        title: '交易方向',
        dataIndex: 'direction',
        key: 'direction',
        render: (value: TransactionOut['direction']) => TRADE_DIRECTION_LABELS[value],
      },
      {
        title: '交易日期',
        dataIndex: 'tradeDate',
        key: 'tradeDate',
        sorter: true,
        sortOrder,
      },

      {
        title: '操作',
        key: 'actions',
        render: (_value: unknown, record: TransactionOut) => (
          <Popconfirm
            title="确认删除这笔交易吗？"
            okText="确认删除"
            cancelText="取消"
            onConfirm={() => this.props.onDelete(record.id)}
          >
            <Button
              aria-label="删除交易"
              className={styles.deleteButton}
              type="link"
              danger
            >
              删除
            </Button>
          </Popconfirm>
        ),
      },
    ];
  }

  /** 根据传入的分页 props 构造 antd Table 分页配置；缺少任一字段则禁用分页。 */
  private renderPagination(): false | NonNullable<TableProps<TransactionOut>['pagination']> {
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
    const { loading } = this.props;
    return (
      <section className={styles.panel} aria-label="历史交易面板">
        <div className={styles.table}>
          <Table<TransactionOut>
            aria-label="历史交易表格"
            columns={this.columns()}
            dataSource={this.uniqueItems()}
            loading={loading}
            locale={{ emptyText: '暂无数据' }}
            pagination={this.renderPagination()}
            rowKey={(record) => record.id}
            onChange={this.handleTableChange}
          />
        </div>
      </section>
    );
  }
}
