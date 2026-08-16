import React from 'react';
import { Button, Popconfirm, Table, Tag } from 'antd';
import type { TableProps } from 'antd';
import type { TransactionOut } from '../../../api/types';
import type { SortOrder } from '../../../domain/ledger/constants';
import type { ProductScope } from '../../../domain/ledger/LedgerQueryState';
import {
  PRODUCT_TYPE_LABELS,
  TRADE_DIRECTION_LABELS,
  TRADE_VALUE_LABELS,
} from '../../../domain/ledger/labels';
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
  /** 产品历史交易范围；即使范围结果为空也可展示。 */
  readonly scope?: ProductScope | null;
  /** 交易日期排序变化回调。 */
  readonly onSortChange: (order: SortOrder | null) => void;
  /** 确认删除后的回调；id 不向用户展示。 */
  readonly onDelete: (transactionId: number) => void;
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

  /** 把 antd 排序状态转换为领域排序码；只有交易日期列可触发。 */
  private readonly handleTableChange: TableChangeHandler = (
    _pagination,
    _filters,
    sorter,
  ): void => {
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

  /** 7 个数据列与 1 个删除操作列；不定义 id 或编辑列。 */
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
        title: '净值/单价', dataIndex: 'transactionPrice', key: 'transactionPrice',
        render: (value: string, record: TransactionOut) => `${TRADE_VALUE_LABELS[record.productType].price}：${value}`,
      },
      {
        title: '份额/数量', dataIndex: 'transactionQuantity', key: 'transactionQuantity',
        render: (value: string, record: TransactionOut) => `${TRADE_VALUE_LABELS[record.productType].quantity}：${value}`,
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

  public override render(): React.ReactNode {
    const { loading, scope } = this.props;
    return (
      <section className={styles.panel} aria-label="历史交易面板">
        {scope != null && (
          <div className={styles.scope} aria-label="产品历史交易范围">
            <Tag color="blue">
              产品范围：{PRODUCT_TYPE_LABELS[scope.productType]} / {scope.productCode}
            </Tag>
          </div>
        )}
        <div className={styles.table}>
          <Table<TransactionOut>
            aria-label="历史交易表格"
            columns={this.columns()}
            dataSource={this.uniqueItems()}
            loading={loading}
            locale={{ emptyText: '暂无数据' }}
            pagination={false}
            rowKey={(record) => record.id}
            onChange={this.handleTableChange}
          />
        </div>
      </section>
    );
  }
}
