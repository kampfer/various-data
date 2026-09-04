import React from 'react';
import { Button, Empty, Table, Tag } from 'antd';
import type { TableProps } from 'antd';
import dayjs from 'dayjs';
import type { AccountOut } from '../../../api/types';
import { accountTypeLabel } from '../../../domain/ledger/labels';
import styles from './index.module.scss';

type AccountColumns = NonNullable<TableProps<AccountOut>['columns']>;

export interface AccountListProps {
  readonly items: readonly AccountOut[];
  readonly loading: boolean;
  readonly updatingId: number | null;
  readonly onEditRemark: (account: AccountOut) => void;
  readonly onToggleStatus: (account: AccountOut) => void;
}

/** 投资账户身份列表；状态操作只改变启用状态，不删除账户或历史交易。 */
const AccountList: React.FC<AccountListProps> = ({
  items,
  loading,
  updatingId,
  onEditRemark,
  onToggleStatus,
}) => {
  const columns: AccountColumns = [
    { title: '账户名称', dataIndex: 'name', key: 'name' },
    {
      title: '账户类型',
      dataIndex: 'accountType',
      key: 'accountType',
      render: (value: string) => accountTypeLabel(value),
    },
    {
      title: '机构/平台',
      dataIndex: 'institution',
      key: 'institution',
      render: (value: string | null) => value || '—',
    },
    {
      title: '状态',
      dataIndex: 'isActive',
      key: 'isActive',
      render: (value: boolean) => (
        <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      render: (value: string | null) => value || '—',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_value: unknown, record: AccountOut) => (
        <div className={styles.actions}>
          <Button
            type="link"
            className={styles.actionButton}
            onClick={() => onEditRemark(record)}
            disabled={updatingId !== null}
          >
            编辑备注
          </Button>
          <Button
            type="link"
            danger={record.isActive}
            className={styles.actionButton}
            loading={updatingId === record.id}
            disabled={updatingId !== null && updatingId !== record.id}
            onClick={() => onToggleStatus(record)}
          >
            {record.isActive ? '停用' : '启用'}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className={styles.panel}>
      <Table<AccountOut>
        rowKey="id"
        className={styles.table}
        columns={columns}
        dataSource={[...items]}
        loading={loading}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无投资账户" /> }}
        pagination={false}
      />
    </div>
  );
};

export default AccountList;
