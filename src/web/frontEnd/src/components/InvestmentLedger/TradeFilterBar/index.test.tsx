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
  it('产品名称与产品代码搜索分别通过回车应用，并可共同保留为查询条件', () => {
    const patches: Partial<LedgerQuerySnapshot>[] = [];
    render(
      <TradeFilterBar
        query={createQuery()}
        module="holdings"
        onApply={(patch) => patches.push(patch)}
        onClearScope={() => undefined}
      />,
    );

    const productNameInput = screen.getByLabelText('产品名称搜索');
    fireEvent.change(productNameInput, { target: { value: '成长基金' } });
    fireEvent.keyDown(productNameInput, { key: 'Enter', code: 'Enter' });
    const productCodeInput = screen.getByLabelText('产品代码搜索');
    fireEvent.change(productCodeInput, { target: { value: 'F001' } });
    fireEvent.keyDown(productCodeInput, { key: 'Enter', code: 'Enter' });

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

    const productNameInput = screen.getByLabelText('产品名称搜索');
    fireEvent.change(productNameInput, { target: { value: '名'.repeat(101) } });
    fireEvent.keyDown(productNameInput, { key: 'Enter', code: 'Enter' });

    expect(patches).toEqual([]);
    await waitFor(() => {
      expect(screen.getByText('搜索值不能为空，且不能超过 100 个字符')).toBeInTheDocument();
    });
  });

  it('筛选栏不再显示日期、搜索与清除操作按钮', () => {
    render(
      <TradeFilterBar
        query={createQuery({ startDate: '2024-01-01', endDate: '2024-01-31' })}
        module="history"
        onApply={() => undefined}
        onClearScope={() => undefined}
      />,
    );

    expect(screen.queryByRole('button', { name: '应用日期范围' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '搜索产品名称' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '搜索产品代码' })).not.toBeInTheDocument();
  });

  it('历史交易产品范围可通过标签关闭图标移除', () => {
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
    fireEvent.click(screen.getByLabelText('清除范围'));
    expect(clearCount).toBe(1);
  });
});
