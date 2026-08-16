import React from 'react';
import { render, screen } from '@testing-library/react';
import type { TransactionOut } from '../../../api/types';
import TradeHistoryPanel from './index';
const items: TransactionOut[] = [
  { id: 1, productType: 'FUND', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2.5', direction: 'BUY', tradeDate: '2024-01-01' },
  { id: 2, productType: 'STOCK', productName: '股票', productCode: 'S001', transactionPrice: '10.123', transactionQuantity: '100', direction: 'SELL', tradeDate: '2024-01-02' },
];
describe('TradeHistoryPanel', () => {
  it('按每行产品类型展示动态标签，并保持 canonical DTO 字段', () => {
    render(<TradeHistoryPanel items={items} loading={false} tradeDateOrder={null} onSortChange={() => undefined} onDelete={() => undefined} />);
    expect(screen.getByText('净值：1.2345')).toBeInTheDocument(); expect(screen.getByText('份额：2.5')).toBeInTheDocument();
    expect(screen.getByText('单价：10.123')).toBeInTheDocument(); expect(screen.getByText('数量：100')).toBeInTheDocument();
    expect(screen.queryByText('交易单价')).not.toBeInTheDocument(); expect(screen.queryByText('交易数量')).not.toBeInTheDocument();
  });
});
