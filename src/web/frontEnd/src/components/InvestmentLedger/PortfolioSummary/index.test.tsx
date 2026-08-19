import React from 'react';
import { render, screen } from '@testing-library/react';
import type { PortfolioStatisticsOut } from '../../../api/types';
import PortfolioSummary from './index';

const portfolio: PortfolioStatisticsOut = {
  totalPosition: { available: true, value: '1000.00', unavailableReason: null },
  totalPositionQuantity: { available: true, value: '88', unavailableReason: null },
  totalProfit: { available: true, value: '80.00', unavailableReason: null },
  totalProfitRate: { available: true, value: '0.08', unavailableReason: null },
  totalAnnualizedRate: { available: false, value: null, unavailableReason: '部分产品不可年化' },
};

describe('PortfolioSummary', () => {
  it('通过 Descriptions 与 MetricValue 渲染五项指标', () => {
    render(<PortfolioSummary portfolio={portfolio} loading={false} />);

    expect(screen.getByText('总持仓')).toBeInTheDocument();
    expect(screen.getByText('1000.00 元')).toBeInTheDocument();
    expect(screen.getByText('总持仓量')).toBeInTheDocument();
    expect(screen.getByText('88')).toBeInTheDocument();
    expect(screen.queryByText('88 元')).not.toBeInTheDocument();
    expect(screen.getByText('总收益')).toBeInTheDocument();
    expect(screen.getByText('80.00 元')).toBeInTheDocument();
    expect(screen.getByText('总收益率')).toBeInTheDocument();
    expect(screen.getByText('0.08 %')).toBeInTheDocument();
    expect(screen.getByText('总年化收益率')).toBeInTheDocument();
    expect(screen.getByText('不可用')).toBeInTheDocument();
  });

  it('统计尚未取得时显示骨架且不伪造 0 值', () => {
    const { container } = render(<PortfolioSummary portfolio={null} loading />);

    expect(container.querySelector('.ant-skeleton')).toBeInTheDocument();
    expect(screen.queryByText(/0 元|0 %/)).not.toBeInTheDocument();
    expect(container.querySelector('[aria-label="投资组合统计"][style]')).toBeNull();
  });
});
