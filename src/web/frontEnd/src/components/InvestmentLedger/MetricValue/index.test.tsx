import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import MetricValue from './index';

describe('MetricValue', () => {
  it('不可用时显示不可用并通过 Tooltip 给出中文原因，且不以 0 代替', async () => {
    render(
      <MetricValue
        kind="amount"
        metric={{ available: false, value: null, unavailableReason: '缺少最新估值' }}
      />,
    );

    const unavailable = screen.getByText('不可用');
    expect(unavailable).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    fireEvent.mouseOver(unavailable);
    expect(await screen.findByRole('tooltip')).toHaveTextContent('缺少最新估值');
  });

  it('可用值只追加对应单位，不修改后端十进制字符串', () => {
    const { rerender } = render(
      <MetricValue kind="amount" metric={{ available: true, value: '123.45', unavailableReason: null }} />,
    );
    expect(screen.getByText('123.45 元')).toBeInTheDocument();

    rerender(
      <MetricValue kind="rate" metric={{ available: true, value: '0.125', unavailableReason: null }} />,
    );
    expect(screen.getByText('0.125 %')).toBeInTheDocument();

    rerender(
      <MetricValue kind="quantity" metric={{ available: true, value: '88', unavailableReason: null }} />,
    );
    expect(screen.getByText('88')).toBeInTheDocument();
    expect(screen.queryByText('88 元')).not.toBeInTheDocument();
    expect(screen.queryByText('88 %')).not.toBeInTheDocument();
  });
});
