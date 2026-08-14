import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { ValuationDraft } from '../../../api/types';
import ValuationFormModal from './index';

interface HarnessProps {
  readonly initialDraft: ValuationDraft;
  readonly onSubmit: (draft: ValuationDraft) => void;
}

/** 用真实受控状态承载草稿，覆盖与 Redux 容器相同的交互方式。 */
const ValuationHarness = ({ initialDraft, onSubmit }: HarnessProps): React.ReactElement => {
  const [draft, setDraft] = useState<ValuationDraft>(initialDraft);
  return (
    <ValuationFormModal
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

describe('ValuationFormModal', () => {
  it('通过 labels 展示产品类型并以英文码提交有效估值', async () => {
    const submitted: ValuationDraft[] = [];
    render(<ValuationHarness initialDraft={{}} onSubmit={(draft) => submitted.push(draft)} />);

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '产品类型' }));
    fireEvent.click(within(await screen.findByRole('listbox')).getByRole('option', { name: '股票' }));
    fireEvent.change(screen.getByLabelText('产品代码'), { target: { value: '600000' } });
    fireEvent.change(screen.getByLabelText('估值日期'), { target: { value: '2024-06-30' } });
    fireEvent.change(screen.getByLabelText('估值单价'), { target: { value: '9.87' } });
    fireEvent.click(screen.getByRole('button', { name: '保存估值' }));

    await waitFor(() => expect(submitted).toEqual([{
      productType: 'STOCK', productCode: '600000', valuationDate: '2024-06-30', unitPrice: '9.87',
    }]));
  });

  it('无效提交逐字段显示错误、保留原值且不调用提交回调', async () => {
    const submitted: ValuationDraft[] = [];
    const invalidDraft: ValuationDraft = {
      productType: null,
      productCode: 'V'.repeat(33),
      valuationDate: '2023-02-29',
      unitPrice: '1000000000.00',
    };
    render(<ValuationHarness initialDraft={invalidDraft} onSubmit={(draft) => submitted.push(draft)} />);

    fireEvent.click(screen.getByRole('button', { name: '保存估值' }));

    await waitFor(() => {
      expect(screen.getByText('产品代码不能超过 32 个字符')).toBeInTheDocument();
      expect(screen.getByText('估值日期必须为有效日历日期，格式为 YYYY-MM-DD')).toBeInTheDocument();
      expect(screen.getByText('估值单价必须在 0 至 999999999.99 之间')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('产品代码')).toHaveValue('V'.repeat(33));
    expect(screen.getByLabelText('估值日期')).toHaveValue('2023-02-29');
    expect(screen.getByLabelText('估值单价')).toHaveValue('1000000000.00');
    expect(submitted).toEqual([]);
  });

  it('映射外部字段错误并保留估值草稿', () => {
    render(
      <ValuationFormModal
        visible
        draft={{ unitPrice: '12.345' }}
        fieldErrors={[{ field: 'unitPrice', code: 'INVALID_SCALE', message: '服务端估值单价错误' }]}
        submitting={false}
        onChange={() => undefined}
        onSubmit={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(screen.getByText('服务端估值单价错误')).toBeInTheDocument();
    expect(screen.getByLabelText('估值单价')).toHaveValue('12.345');
  });
});
