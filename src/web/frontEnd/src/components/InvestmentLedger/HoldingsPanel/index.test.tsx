import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
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
  accounts: [{ accountId: 1, accountName: '基金账户', accountInstitution: '示例机构' }],
  position: available('325.00'),
  positionQuantity: available('100'),
  latestValuationUnitPrice: available('3.25'),
  latestValuationDate: '2024-01-05',
  totalProfit: available('25.00'),
  totalProfitRate: available('0.0833'),
  annualizedRate: available('0.1012'),
}];

const baseHolding: HoldingOut = holdings[0]!;

/** 两条数据用于验证前端排序：中证500 持仓额更小、总收益更大。 */
const multipleHoldings: HoldingOut[] = [
  baseHolding,
  {
    productType: 'FUND',
    productName: '中证500ETF',
    productCode: '510500',
    accounts: [{ accountId: 2, accountName: '定投账户', accountInstitution: '示例机构' }],
    position: available('120.00'),
    positionQuantity: available('60'),
    latestValuationUnitPrice: available('2.00'),
    latestValuationDate: '2024-01-05',
    totalProfit: available('40.00'),
    totalProfitRate: available('0.5000'),
    annualizedRate: available('0.6000'),
  },
];

const renderPanel = (
  props: Partial<React.ComponentProps<typeof HoldingsPanel>> = {},
): ReturnType<typeof render> => render(
  <HoldingsPanel
    items={holdings}
    loading={false}
    onViewTransactions={() => undefined}
    onReadOnlyIntent={() => undefined}
    {...props}
  />,
);

/** 读取 tbody 中每一行第二列（产品名称）文本，作为排序结果断言依据。 */
const productNameOrder = (): string[] =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[1]?.textContent?.trim() ?? '');

describe('HoldingsPanel', () => {
  it('渲染持仓指标、净值和日期列且无逐笔、展开或写控件', () => {
    const { container } = renderPanel();

    expect(screen.getAllByRole('columnheader').map((node) => node.textContent?.trim())).toEqual([
      '产品类型', '产品名称', '产品代码', '交易账户', '持仓量', '持仓额', '最新净值', '最新净值日期', '总收益', '总收益率', '年化收益率',
    ]);
    expect(screen.getByText('基金')).toBeInTheDocument();
    expect(screen.getByText('示例机构 - 基金账户')).toBeInTheDocument();
    expect(screen.getByText('3.25')).toBeInTheDocument();
    expect(screen.getByText('2024-01-05')).toBeInTheDocument();
    expect(screen.queryByText('100 元')).not.toBeInTheDocument();
    expect(screen.queryByText('100 %')).not.toBeInTheDocument();
    expect(screen.queryByText(/交易单价|新增|删除|编辑/)).not.toBeInTheDocument();
    expect(container.querySelector('.ant-table-row-expand-icon')).toBeNull();
    expect(screen.getByLabelText('持仓面板')).not.toHaveAttribute('style');
    expect(screen.getByRole('button', { name: '查看沪深300ETF的历史交易' })).not.toHaveAttribute('style');
  });

  it('不渲染分页控件，直接展示全部条目', () => {
    const { container } = renderPanel({ items: multipleHoldings });

    expect(container.querySelector('.ant-pagination')).toBeNull();
    expect(container.querySelectorAll('tbody .ant-table-row')).toHaveLength(2);
  });

  it('以产品名称提供历史入口，并传递产品代码与名称', () => {
    const onViewTransactions = vi.fn();
    renderPanel({ onViewTransactions });

    fireEvent.click(screen.getByRole('button', { name: '查看沪深300ETF的历史交易' }));
    expect(onViewTransactions).toHaveBeenCalledOnce();
    expect(onViewTransactions).toHaveBeenCalledWith({ productCode: '510300', productName: '沪深300ETF' });
  });

  it('持仓额与总收益支持前端排序，点击列头即在本地重排', () => {
    renderPanel({ items: multipleHoldings });

    // 默认按来源顺序：沪深300 在前
    expect(productNameOrder()).toEqual(['沪深300ETF', '中证500ETF']);

    // 点击“持仓额”升序：中证500(120) 在前
    fireEvent.click(screen.getByRole('columnheader', { name: /^持仓额$/ }));
    expect(productNameOrder()).toEqual(['中证500ETF', '沪深300ETF']);

    // 再次点击变降序：沪深300(325) 在前
    fireEvent.click(screen.getByRole('columnheader', { name: /^持仓额$/ }));
    expect(productNameOrder()).toEqual(['沪深300ETF', '中证500ETF']);

    // 切到“总收益”升序：沪深300(25) 在前
    fireEvent.click(screen.getByRole('columnheader', { name: /总收益$/ }));
    expect(productNameOrder()).toEqual(['沪深300ETF', '中证500ETF']);
  });

  it('年化收益率支持前端排序', () => {
    renderPanel({ items: multipleHoldings });

    // 点击“年化收益率”升序：沪深300(0.1012) 在前
    fireEvent.click(screen.getByRole('columnheader', { name: /^年化收益率$/ }));
    expect(productNameOrder()).toEqual(['沪深300ETF', '中证500ETF']);
  });

  it('产品名称、产品代码、交易账户列提供 antd 自带筛选入口', () => {
    const { container } = renderPanel({ items: multipleHoldings });

    const headers = screen.getAllByRole('columnheader');
    const nameHeader = headers.find((node) => node.textContent?.trim() === '产品名称');
    const codeHeader = headers.find((node) => node.textContent?.trim() === '产品代码');
    const accountHeader = headers.find((node) => node.textContent?.trim() === '交易账户');

    expect(nameHeader?.querySelector('.ant-table-filter-trigger')).not.toBeNull();
    expect(codeHeader?.querySelector('.ant-table-filter-trigger')).not.toBeNull();
    expect(accountHeader?.querySelector('.ant-table-filter-trigger')).not.toBeNull();
    // 持仓量列仅排序、不提供筛选
    const quantityHeader = headers.find((node) => node.textContent?.trim() === '持仓量');
    expect(quantityHeader?.querySelector('.ant-table-filter-trigger')).toBeNull();
    expect(container).toBeTruthy();
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

    expect(screen.getAllByRole('columnheader')).toHaveLength(11);
    expect(container.querySelectorAll('tbody .ant-table-row')).toHaveLength(0);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
