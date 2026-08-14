import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { TransactionOut } from '../../../api/types';
import TradeHistoryPanel from './index';

const transactions: TransactionOut[] = [
  {
    id: 101,
    productType: 'FUND',
    productName: '沪深300ETF',
    productCode: '510300',
    unitPrice: '3.25',
    quantity: 100,
    direction: 'BUY',
    tradeDate: '2024-01-02',
  },
  {
    id: 102,
    productType: 'STOCK',
    productName: '示例股票',
    productCode: '600000',
    unitPrice: '10.50',
    quantity: 200,
    direction: 'SELL',
    tradeDate: '2024-02-03',
  },
];

const renderPanel = (
  props: Partial<React.ComponentProps<typeof TradeHistoryPanel>> = {},
): ReturnType<typeof render> => render(
  <TradeHistoryPanel
    items={transactions}
    loading={false}
    tradeDateOrder={null}
    onSortChange={() => undefined}
    onDelete={() => undefined}
    {...props}
  />,
);

describe('TradeHistoryPanel', () => {
  it('按规定顺序渲染 7 个独立数据列和删除操作列，不展示 id 或编辑入口', () => {
    renderPanel();

    const headers = screen.getAllByRole('columnheader').map((header) => header.textContent?.trim());
    expect(headers).toEqual([
      '产品类型', '产品名称', '产品代码', '交易单价',
      '交易数量', '交易方向', '交易日期', '操作',
    ]);
    expect(screen.queryByText('101')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /编辑/ })).not.toBeInTheDocument();
    expect(screen.getByText('基金')).toBeInTheDocument();
    expect(screen.getByText('股票')).toBeInTheDocument();
    expect(screen.getByText('买入')).toBeInTheDocument();
    expect(screen.getByText('卖出')).toBeInTheDocument();
  });

  it('每笔交易恰占一行，并按交易 id 去除重复输入', () => {
    renderPanel({ items: [...transactions, transactions[0]!] });

    const rows = screen.getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(screen.getAllByText('沪深300ETF')).toHaveLength(1);
    expect(within(rows[1]!).getByText('510300')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('600000')).toBeInTheDocument();
  });

  it('确认后仅以内部交易 id 发起删除', async () => {
    const onDelete = vi.fn();
    renderPanel({ onDelete });

    fireEvent.click(screen.getAllByRole('button', { name: '删除交易' })[0]!);
    fireEvent.click(await screen.findByRole('button', { name: '确认删除' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledWith(101);
  });
});

describe('TradeHistoryPanel 范围、排序与空结果', () => {
  it('产品历史范围标签复用产品类型中文映射并展示产品代码', () => {
    renderPanel({ scope: { productType: 'STOCK', productCode: '600000' }, items: [] });

    expect(screen.getByLabelText('产品历史交易范围')).toHaveTextContent('产品范围：股票 / 600000');
  });

  it('交易日期表头触发排序并反映受控排序方向', () => {
    const onSortChange = vi.fn();
    const { rerender } = renderPanel({ onSortChange });
    const dateHeader = screen.getByRole('columnheader', { name: /交易日期/ });

    fireEvent.click(dateHeader);
    expect(onSortChange).toHaveBeenCalledWith('asc');

    rerender(
      <TradeHistoryPanel
        items={transactions}
        loading={false}
        tradeDateOrder="asc"
        onSortChange={onSortChange}
        onDelete={() => undefined}
      />,
    );
    expect(screen.getByRole('columnheader', { name: /交易日期/ })).toHaveAttribute('aria-sort', 'ascending');
  });

  it('空结果渲染 0 个数据行并保留全部列头', () => {
    const { container } = renderPanel({ items: [] });

    expect(screen.getAllByRole('columnheader')).toHaveLength(8);
    expect(container.querySelectorAll('tbody .ant-table-row')).toHaveLength(0);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('组件自有容器与控件不产生行内 style 属性', () => {
    const { container } = renderPanel({
      scope: { productType: 'FUND', productCode: '510300' },
    });
    expect(container.querySelector('[aria-label="历史交易面板"][style]')).toBeNull();
    expect(container.querySelector('[aria-label="产品历史交易范围"][style]')).toBeNull();
    expect(container.querySelector('.deleteButton[style]')).toBeNull();
  });
});
