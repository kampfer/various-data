import React from 'react';
import { render, screen } from '@testing-library/react';
import type { TransactionOut } from '../../../api/types';
import TradeHistoryPanel from './index';
const items: TransactionOut[] = [
  // 基金：净值 1.23 → 展示为 1.2300（4 位小数），第 5 位四舍五入 1.23454→1.2345
  { id: 1, accountId: 3, accountName: '基金账户', accountInstitution: '示例机构', productType: 'FUND', productName: '基金', productCode: 'F001', transactionPrice: '1.2345', transactionQuantity: '2.5', fee: '0', direction: 'BUY', tradeDate: '2024-01-01' },
  // 股票：单价保持原样 10.123（不格式化）
  { id: 2, accountId: null, accountName: null, accountInstitution: null, productType: 'STOCK', productName: '股票', productCode: 'S001', transactionPrice: '10.123', transactionQuantity: '100', fee: '5.00', direction: 'SELL', tradeDate: '2024-01-02' },
  // 理财：净值 0.99999 → 展示为 1.0000（四舍五入到 4 位）
  { id: 3, accountId: null, accountName: null, accountInstitution: null, productType: 'WEALTH', productName: '理财', productCode: 'W001', transactionPrice: '0.99999', transactionQuantity: '10000', fee: '0', direction: 'BUY', tradeDate: '2024-01-03' },
];
describe('TradeHistoryPanel', () => {
  it('按产品类型格式化净值/单价（基金/理财 4 位，股票原样），展示费用与交易金额列', () => {
    render(<TradeHistoryPanel items={items} loading={false} tradeDateOrder={null} onSortChange={() => undefined} onDelete={() => undefined} />);
    // 净值/单价列：基金 1.23450000 → 1.2345 已是 4 位，展示 1.2345？不，1.2345 已经 4 位了，就是 1.2345
    // 不对，实际数据 transactionPrice 是 '1.2345'（4 位小数），格式化后还是 '1.2345'
    expect(screen.getByText('1.2345')).toBeInTheDocument();
    // 股票单价保持原样：10.123（3 位小数，不格式化）
    expect(screen.getByText('10.123')).toBeInTheDocument();
    // 理财 0.99999 → 四舍五入到 4 位：1.0000
    expect(screen.getByText('1.0000')).toBeInTheDocument();
    // 份额/数量列保持原样（不格式化）
    expect(screen.getByText('2.5')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    // 费用列直接展示落库值（需求 6.5）；两条记录 fee=0，所以至少有 2 个单元格显示 '0'
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('5.00')).toBeInTheDocument();
    // 交易金额列由前端计算展示，固定两位小数（需求 6.5、6.6）
    expect(screen.getByText('3.09')).toBeInTheDocument();
    expect(screen.getByText('1017.30')).toBeInTheDocument();
    // 中性列标题
    expect(screen.getByText('示例机构 - 基金账户')).toBeInTheDocument();
    expect(screen.getAllByText('未关联账户')).toHaveLength(2);
    expect(screen.getByText('净值/单价')).toBeInTheDocument();
    expect(screen.getByText('份额/数量')).toBeInTheDocument();
    expect(screen.getByText('费用')).toBeInTheDocument();
    expect(screen.getByText('交易金额')).toBeInTheDocument();
  });
});
