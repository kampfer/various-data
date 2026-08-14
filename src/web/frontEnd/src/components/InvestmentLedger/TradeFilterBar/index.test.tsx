import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { LedgerQuerySnapshot } from '../../../domain/ledger/LedgerQueryState';
import { productTypeOptions, tradeDirectionOptions } from '../../../domain/ledger/labels';
import TradeFilterBar from './index';

const createQuery = (patch: Partial<LedgerQuerySnapshot> = {}): LedgerQuerySnapshot => ({
  productType: null,
  direction: null,
  startDate: null,
  endDate: null,
  productName: null,
  productCode: null,
  tradeDateOrder: null,
  holdingSortField: null,
  holdingSortOrder: null,
  page: 1,
  pageSize: 20,
  scopeProductType: null,
  scopeProductCode: null,
  ...patch,
});

describe('TradeFilterBar', () => {
  it('产品类型与交易方向选项由标签映射生成，并以英文码提交', async () => {
    const patches: Partial<LedgerQuerySnapshot>[] = [];
    render(
      <TradeFilterBar
        query={createQuery()}
        module="history"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );

    expect(productTypeOptions()).toEqual([
      { value: 'WEALTH', label: '理财' },
      { value: 'FUND', label: '基金' },
      { value: 'STOCK', label: '股票' },
    ]);
    expect(tradeDirectionOptions()).toEqual([
      { value: 'BUY', label: '买入' },
      { value: 'SELL', label: '卖出' },
    ]);

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '产品类型筛选' }));
    const productList = await screen.findByRole('listbox');
    fireEvent.click(within(productList).getByRole('option', { name: '基金' }));

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '交易方向筛选' }));
    const directionList = await screen.findByRole('listbox');
    expect(within(directionList).getByRole('option', { name: '买入' })).toBeInTheDocument();
    expect(within(directionList).getByRole('option', { name: '卖出' })).toBeInTheDocument();
    fireEvent.click(within(directionList).getByRole('option', { name: '卖出' }));

    expect(patches).toEqual([{ productType: 'FUND' }, { direction: 'SELL' }]);
  });
  it('产品名称与产品代码搜索分别应用，并可共同保留为查询条件', () => {
    const patches: Partial<LedgerQuerySnapshot>[] = [];
    render(
      <TradeFilterBar
        query={createQuery()}
        module="holdings"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );

    fireEvent.change(screen.getByLabelText('产品名称搜索'), { target: { value: '成长基金' } });
    fireEvent.click(screen.getByRole('button', { name: '搜索产品名称' }));
    fireEvent.change(screen.getByLabelText('产品代码搜索'), { target: { value: 'F001' } });
    fireEvent.click(screen.getByRole('button', { name: '搜索产品代码' }));

    expect(patches).toEqual([
      { productName: '成长基金' },
      { productCode: 'F001' },
    ]);
  });

  it('无效搜索值仅显示错误，不回调应用查询', async () => {
    const patches: Partial<LedgerQuerySnapshot>[] = [];
    render(
      <TradeFilterBar
        query={createQuery()}
        module="history"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );

    fireEvent.change(screen.getByLabelText('产品名称搜索'), { target: { value: '名'.repeat(101) } });
    fireEvent.click(screen.getByRole('button', { name: '搜索产品名称' }));

    expect(patches).toEqual([]);
    await waitFor(() => {
      expect(screen.getByText('搜索值不能为空，且不能超过 100 个字符')).toBeInTheDocument();
    });
  });
  it('日期范围先校验再提交，无效范围只显示错误', async () => {
    const patches: Partial<LedgerQuerySnapshot>[] = [];
    const { rerender } = render(
      <TradeFilterBar
        query={createQuery({ startDate: '2024-01-01', endDate: '2024-01-31' })}
        module="history"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '应用日期范围' }));
    expect(patches).toEqual([{ startDate: '2024-01-01', endDate: '2024-01-31' }]);

    patches.length = 0;
    rerender(
      <TradeFilterBar
        query={createQuery({ startDate: '2024-02-01', endDate: '2024-01-01' })}
        module="history"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: '应用日期范围' }));

    expect(patches).toEqual([]);
    await waitFor(() => {
      expect(screen.getByText('交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期')).toBeInTheDocument();
    });
  });

  it('历史交易产品范围可见且只能通过清除范围回调移除', () => {
    let clearCount = 0;
    render(
      <TradeFilterBar
        query={createQuery({ scopeProductType: 'STOCK', scopeProductCode: '600000' })}
        module="history"
        onApply={() => undefined}
        onClearScope={() => { clearCount += 1; }}
      />,
    );

    expect(screen.getByText('产品范围：600000')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '清除范围' }));
    expect(clearCount).toBe(1);
  });
});
