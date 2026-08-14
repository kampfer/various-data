import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { TradeDraft } from '../../../api/types';
import TradeFormModal from './index';

interface HarnessProps {
  readonly initialDraft: TradeDraft;
  readonly onSubmit: (draft: TradeDraft) => void;
}

/** 用真实受控状态承载草稿，覆盖与 Redux 容器相同的交互方式。 */
const TradeHarness = ({ initialDraft, onSubmit }: HarnessProps): React.ReactElement => {
  const [draft, setDraft] = useState<TradeDraft>(initialDraft);
  return (
    <TradeFormModal
      visible
      draft={draft}
      fieldErrors={[]}
      submitting={false}
      onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
      onSubmit={onSubmit}
      onCancel={() => undefined}
    />
  );
};

describe('TradeFormModal', () => {
  it('通过 labels 展示选择项并以英文码提交完整新交易', async () => {
    const submitted: TradeDraft[] = [];
    render(<TradeHarness initialDraft={{}} onSubmit={(draft) => submitted.push(draft)} />);

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '产品类型' }));
    fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '基金' }));
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '交易方向' }));
    fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '买入' }));
    fireEvent.change(screen.getByLabelText('产品名称'), { target: { value: '成长基金' } });
    fireEvent.change(screen.getByLabelText('产品代码'), { target: { value: 'F001' } });
    fireEvent.change(screen.getByLabelText('交易单价'), { target: { value: '12.30' } });
    fireEvent.change(screen.getByLabelText('交易数量'), { target: { value: '10' } });
    fireEvent.change(screen.getByLabelText('交易日期'), { target: { value: '2024-02-29' } });
    fireEvent.click(screen.getByRole('button', { name: '创建交易' }));

    await waitFor(() => expect(submitted).toEqual([{
      productType: 'FUND', direction: 'BUY', productName: '成长基金', productCode: 'F001',
      unitPrice: '12.30', quantity: '10', tradeDate: '2024-02-29',
    }]));
  });

  it('无效提交逐字段显示错误、保留原值且不调用提交回调', async () => {
    const submitted: TradeDraft[] = [];
    const invalidDraft: TradeDraft = {
      productType: null,
      direction: null,
      productName: '',
      productCode: 'C'.repeat(33),
      unitPrice: '1.2',
      quantity: '1.5',
      tradeDate: '2024-02-30',
    };
    render(<TradeHarness initialDraft={invalidDraft} onSubmit={(draft) => submitted.push(draft)} />);

    fireEvent.click(screen.getByRole('button', { name: '创建交易' }));

    await waitFor(() => {
      expect(screen.getByText('产品名称不能为空')).toBeInTheDocument();
      expect(screen.getByText('产品代码不能超过 32 个字符')).toBeInTheDocument();
      expect(screen.getByText('交易单价必须为大于 0 且恰有两位小数的数值')).toBeInTheDocument();
      expect(screen.getByText('交易数量必须为大于 0 的整数')).toBeInTheDocument();
      expect(screen.getByText('交易日期必须为有效日历日期，格式为 YYYY-MM-DD')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('产品代码')).toHaveValue('C'.repeat(33));
    expect(screen.getByLabelText('交易单价')).toHaveValue('1.2');
    expect(screen.getByLabelText('交易数量')).toHaveValue('1.5');
    expect(screen.getByLabelText('交易日期')).toHaveValue('2024-02-30');
    expect(submitted).toEqual([]);
  });

  it('映射外部字段错误到 Form.Item 且不暴露编辑既有交易入口', () => {
    render(
      <TradeFormModal
        visible
        draft={{ productName: '原值' }}
        fieldErrors={[{ field: 'productName', code: 'TOO_LONG', message: '服务端产品名称错误' }]}
        submitting={false}
        onChange={() => undefined}
        onSubmit={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(screen.getByText('服务端产品名称错误')).toBeInTheDocument();
    expect(screen.getByLabelText('产品名称')).toHaveValue('原值');
    expect(screen.queryByRole('button', { name: /编辑|更新/ })).not.toBeInTheDocument();
  });
});
