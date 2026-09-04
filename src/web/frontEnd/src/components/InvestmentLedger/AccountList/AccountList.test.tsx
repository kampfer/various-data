import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { AccountOut } from '../../../api/types';
import AccountList from './index';

const account: AccountOut = {
  id: 2,
  name: '我的证券账户',
  accountType: 'STOCK',
  institution: '示例券商',
  isActive: true,
  remark: '只编辑这条备注',
  createdAt: '2024-01-01T10:00:00',
  updatedAt: '2024-01-01T10:00:00',
};

describe('AccountList', () => {
  it('展示账户身份字段并支持编辑备注和启停状态', () => {
    const onEditRemark = vi.fn();
    const onToggleStatus = vi.fn();
    render(
      <AccountList
        items={[account]}
        loading={false}
        updatingId={null}
        onEditRemark={onEditRemark}
        onToggleStatus={onToggleStatus}
      />,
    );

    expect(screen.getByText('我的证券账户')).toBeInTheDocument();
    expect(screen.getByText('证券账户')).toBeInTheDocument();
    expect(screen.getByText('示例券商')).toBeInTheDocument();
    expect(screen.getByText('只编辑这条备注')).toBeInTheDocument();
    expect(screen.queryByText('删除')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '编辑备注' }));
    expect(onEditRemark).toHaveBeenCalledWith(account);
    fireEvent.click(screen.getByRole('button', { name: '停用' }));
    expect(onToggleStatus).toHaveBeenCalledWith(account);
  });
});
