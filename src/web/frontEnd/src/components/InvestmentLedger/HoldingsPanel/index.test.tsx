import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { message } from 'antd';
import { describe, expect, it, vi } from 'vitest';
import type { HoldingOut } from '../../../api/types';
import HoldingsPanel from './index';

const available = (value: string) => ({
  available: true,
  value,
  unavailableReason: null,
});

const holdings: HoldingOut[] = [{
  productType: 'FUND',
  productName: '沪深300ETF',
  productCode: '510300',
  position: available('325.00'),
  positionQuantity: available('100'),
  totalProfit: available('25.00'),
  totalProfitRate: available('0.0833'),
  annualizedRate: available('0.1012'),
}];

const renderPanel = (
  props: Partial<React.ComponentProps<typeof HoldingsPanel>> = {},
): ReturnType<typeof render> => render(
  <HoldingsPanel
    items={holdings}
    loading={false}
    sortField={null}
    sortOrder={null}
    onSortChange={() => undefined}
    onViewTransactions={() => undefined}
    onReadOnlyIntent={() => undefined}
    {...props}
  />,
);

describe('HoldingsPanel', () => {
  it('恰好渲染 8 个只读汇总列且无逐笔、展开或写控件', () => {
    const { container } = renderPanel();

    expect(screen.getAllByRole('columnheader').map((node) => node.textContent?.trim())).toEqual([
      '产品类型', '产品名称', '产品代码', '持仓额', '持仓量', '总收益', '总收益率', '年化收益率',
    ]);
    expect(screen.getByText('基金')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.queryByText('100 元')).not.toBeInTheDocument();
    expect(screen.queryByText('100 %')).not.toBeInTheDocument();
    expect(screen.queryByText(/交易单价|新增|删除|编辑/)).not.toBeInTheDocument();
    expect(container.querySelector('.ant-table-row-expand-icon')).toBeNull();
    expect(screen.getByLabelText('持仓面板')).not.toHaveAttribute('style');
    expect(screen.getByRole('button', { name: '查看沪深300ETF的历史交易' })).not.toHaveAttribute('style');
  });

  it('以产品名称提供历史入口，并传递产品代码与名称', () => {
    const onViewTransactions = vi.fn();
    renderPanel({ onViewTransactions });

    fireEvent.click(screen.getByRole('button', { name: '查看沪深300ETF的历史交易' }));
    expect(onViewTransactions).toHaveBeenCalledOnce();
    expect(onViewTransactions).toHaveBeenCalledWith({ productCode: '510300', productName: '沪深300ETF' });
  });

  it('持仓与总收益支持升降序，并在取消时清除数值排序', () => {
    const onSortChange = vi.fn();
    const { rerender } = renderPanel({ onSortChange });

    fireEvent.click(screen.getByRole('columnheader', { name: /^持仓额$/ }));
    expect(onSortChange).toHaveBeenLastCalledWith('position', 'asc');
    rerender(
      <HoldingsPanel
        items={holdings}
        loading={false}
        sortField="position"
        sortOrder="asc"
        onSortChange={onSortChange}
        onViewTransactions={() => undefined}
        onReadOnlyIntent={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole('columnheader', { name: /^持仓额$/ }));
    expect(onSortChange).toHaveBeenLastCalledWith('position', 'desc');
    rerender(
      <HoldingsPanel
        items={holdings}
        loading={false}
        sortField="position"
        sortOrder="desc"
        onSortChange={onSortChange}
        onViewTransactions={() => undefined}
        onReadOnlyIntent={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole('columnheader', { name: /^持仓额$/ }));
    expect(onSortChange).toHaveBeenLastCalledWith(null, null);

    rerender(
      <HoldingsPanel
        items={holdings}
        loading={false}
        sortField={null}
        sortOrder={null}
        onSortChange={onSortChange}
        onViewTransactions={() => undefined}
        onReadOnlyIntent={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole('columnheader', { name: /总收益$/ }));
    expect(onSortChange).toHaveBeenLastCalledWith('totalProfit', 'asc');
  });

  it('写意图仅显示只读信息并通知容器', () => {
    const info = vi.spyOn(message, 'info').mockImplementation(() => ({ then: () => undefined }) as never);
    const onReadOnlyIntent = vi.fn();
    const ref = React.createRef<HoldingsPanel>();
    render(
      <HoldingsPanel
        ref={ref}
        items={holdings}
        loading={false}
        sortField={null}
        sortOrder={null}
        onSortChange={() => undefined}
        onViewTransactions={() => undefined}
        onReadOnlyIntent={onReadOnlyIntent}
      />,
    );

    ref.current?.notifyReadOnlyIntent('trade');
    ref.current?.notifyReadOnlyIntent('holding');
    expect(info).toHaveBeenNthCalledWith(1, '请在历史交易记录模块中维护历史交易');
    expect(info).toHaveBeenNthCalledWith(2, '持仓模块仅供查看');
    expect(onReadOnlyIntent.mock.calls).toEqual([['trade'], ['holding']]);
  });

  it('空结果保留全部列头', () => {
    const { container } = renderPanel({ items: [] });

    expect(screen.getAllByRole('columnheader')).toHaveLength(8);
    expect(container.querySelectorAll('tbody .ant-table-row')).toHaveLength(0);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
