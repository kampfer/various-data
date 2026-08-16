import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { TradeDraft } from '../../../api/types';
import TradeFormModal from './index';
const Harness = ({ initialDraft, onSubmit }: { initialDraft: TradeDraft; onSubmit: (draft: TradeDraft) => void }): React.ReactElement => { const [draft, setDraft] = useState(initialDraft); return <TradeFormModal visible draft={draft} fieldErrors={[]} submitting={false} onChange={(patch) => setDraft((old) => ({ ...old, ...patch }))} onSubmit={onSubmit} onCancel={() => undefined} />; };
describe('TradeFormModal', () => {
  it('使用动态标签但以 canonical 字段提交并在切换类型时保留数值', async () => {
    const submitted: TradeDraft[] = []; render(<Harness initialDraft={{ productType: 'FUND', direction: 'BUY', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2.5', tradeDate: '2024-02-29' }} onSubmit={(draft) => submitted.push(draft)} />);
    expect(screen.getByLabelText('净值')).toHaveValue('1.2345'); expect(screen.getByLabelText('份额')).toHaveValue('2.5');
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '产品类型' })); fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '股票' }));
    expect(screen.getByLabelText('单价')).toHaveValue('1.2345'); expect(screen.getByLabelText('数量')).toHaveValue('2.5');
    fireEvent.change(screen.getByLabelText('数量'), { target: { value: '2' } }); fireEvent.click(screen.getByRole('button', { name: '创建交易' }));
    await waitFor(() => expect(submitted).toEqual([{ productType: 'STOCK', direction: 'BUY', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2', tradeDate: '2024-02-29' }]));
  });
  it('以 canonical 错误键回填并保留无效原始文本', async () => {
    render(<Harness initialDraft={{ productType: 'STOCK', transactionPrice: 'NaN', transactionQuantity: '1.5' }} onSubmit={() => undefined} />); fireEvent.click(screen.getByRole('button', { name: '创建交易' }));
    await waitFor(() => expect(screen.getByText('股票数量必须为正整数')).toBeInTheDocument());
    expect(screen.getByLabelText('单价')).toHaveValue('NaN'); expect(screen.getByLabelText('数量')).toHaveValue('1.5');
  });
});
