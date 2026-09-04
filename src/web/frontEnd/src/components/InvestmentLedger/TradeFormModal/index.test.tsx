import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { AccountOut, TradeDraft } from '../../../api/types';
import TradeFormModal from './index';

const accounts: AccountOut[] = [
  { id: 3, name: '基金账户', accountType: 'FUND', institution: '示例机构', isActive: true, remark: null, createdAt: '2024-01-01', updatedAt: '2024-01-01' },
  { id: 4, name: '已停用账户', accountType: 'FUND', institution: '示例机构', isActive: false, remark: null, createdAt: '2024-01-01', updatedAt: '2024-01-01' },
];
const Harness = ({ initialDraft, onSubmit }: { initialDraft: TradeDraft; onSubmit: (draft: TradeDraft) => void }): React.ReactElement => {
  const [draft, setDraft] = useState(initialDraft);
  return <TradeFormModal visible draft={draft} accounts={accounts} fieldErrors={[]} submitting={false} onChange={(patch) => setDraft((old) => ({ ...old, ...patch }))} onSubmit={onSubmit} onCancel={() => undefined} />;
};
describe('TradeFormModal', () => {
  it('使用动态标签但以 canonical 字段提交并在切换类型时保留数值', async () => {
    const submitted: TradeDraft[] = []; render(<Harness initialDraft={{ accountId: 3, productType: 'FUND', direction: 'BUY', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2.5', tradeDate: '2024-02-29' }} onSubmit={(draft) => submitted.push(draft)} />);
    expect(screen.getByLabelText('净值')).toHaveValue('1.2345'); expect(screen.getByLabelText('份额')).toHaveValue('2.5');
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '产品类型' })); fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '股票' }));
    expect(screen.getByLabelText('单价')).toHaveValue('1.2345'); expect(screen.getByLabelText('数量')).toHaveValue('2.5');
    fireEvent.change(screen.getByLabelText('数量'), { target: { value: '2' } }); fireEvent.click(screen.getByRole('button', { name: '创建交易' }));
    await waitFor(() => expect(submitted).toEqual([{ accountId: 3, productType: 'STOCK', direction: 'BUY', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2', tradeDate: '2024-02-29' }]));
  });
  it('以 canonical 错误键回填并保留无效原始文本', async () => {
    render(<Harness initialDraft={{ productType: 'STOCK', transactionPrice: 'NaN', transactionQuantity: '1.5' }} onSubmit={() => undefined} />); fireEvent.click(screen.getByRole('button', { name: '创建交易' }));
    await waitFor(() => expect(screen.getByText('股票数量必须为正整数')).toBeInTheDocument());
    expect(screen.getByLabelText('单价')).toHaveValue('NaN'); expect(screen.getByLabelText('数量')).toHaveValue('1.5');
  });

  it('选择启用交易账户并随交易草稿提交 accountId', async () => {
    const submitted: TradeDraft[] = [];
    render(<Harness initialDraft={{ accountId: null, productType: 'FUND', direction: 'BUY', productName: '基金', productCode: 'F001', transactionPrice: '1.2', transactionQuantity: '1', tradeDate: '2024-02-29' }} onSubmit={(draft) => submitted.push(draft)} />);
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '交易账户' }));
    fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '示例机构 - 基金账户' }));
    fireEvent.click(screen.getByRole('button', { name: '创建交易' }));
    await waitFor(() => expect(submitted[0]?.accountId).toBe(3));
  });

  it('新建交易账户下拉框不显示已停用账户', async () => {
    render(<Harness initialDraft={{ productType: 'STOCK', direction: 'BUY' }} onSubmit={() => undefined} />);

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '交易账户' }));
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByRole('option', { name: '示例机构 - 基金账户' })).toBeInTheDocument();
    expect(within(listbox).queryByRole('option', { name: '示例机构 - 已停用账户' })).not.toBeInTheDocument();
  });

  it('基金类型下输入产品代码触发搜索后无匹配，仍展示空态浮动框（需求 5.4）', async () => {
    window.r = [];
    render(<Harness initialDraft={{ productType: 'FUND', direction: 'BUY' }} onSubmit={() => undefined} />);

    // 仅输入产品代码触发 500ms 防抖搜索；产品名称为只读文本
    fireEvent.change(screen.getByLabelText('产品代码'), { target: { value: '000000' } });
    expect(screen.getByLabelText('产品名称').tagName).toBe('SPAN');

    // 等待防抖结束 + 请求 resolve 后空态浮动框出现（需求 5.4：无匹配仍展示空态提示）
    expect(await screen.findByText('没有匹配的基金', undefined, { timeout: 2000 })).toBeInTheDocument();
    // 空态分支不应渲染 listbox（列表仅在有结果时出现）
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('按产品代码搜索并选择基金后自动回填名称和代码', async () => {
    window.r = [['110011', 'YFDYL', '易方达优选']];
    render(<Harness initialDraft={{ productType: 'FUND', direction: 'BUY' }} onSubmit={() => undefined} />);

    fireEvent.change(screen.getByLabelText('产品代码'), { target: { value: '110011' } });
    const result = await screen.findByRole('button', { name: '选择基金 易方达优选 110011' });
    fireEvent.click(result);

    expect(screen.getByLabelText('产品代码')).toHaveValue('110011');
    expect(screen.getByLabelText('产品名称')).toHaveTextContent('易方达优选');
    expect(screen.getByLabelText('产品名称').tagName).toBe('SPAN');
    window.r = [];
  });
});
