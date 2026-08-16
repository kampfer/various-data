import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import LedgerLayout from './index';

/** 显示子路由位置和导航意图，用于验证布局执行的 URL 导航。 */
const LocationProbe: React.FC = () => {
  const location = useLocation();
  const navigation = (location.state as { ledgerNavigation?: string } | null)?.ledgerNavigation ?? '';
  return <output data-testid="location">{`${location.pathname}|${navigation}`}</output>;
};

const renderLedgerLayout = () => render(
  <MemoryRouter initialEntries={['/investmentLedger/holdings']}>
    <Routes>
      <Route path="/investmentLedger" element={<LedgerLayout />}>
        <Route path="holdings" element={<LocationProbe />} />
        <Route path="history" element={<LocationProbe />} />
      </Route>
    </Routes>
  </MemoryRouter>,
);

describe('LedgerLayout', () => {
  /** Validates: Requirements 2.1, 2.13 */
  it('点击 Menu 后通过 URL 导航并携带模块切换意图', () => {
    renderLedgerLayout();

    expect(screen.getByTestId('location')).toHaveTextContent('/investmentLedger/holdings|');
    fireEvent.click(screen.getByRole('menuitem', { name: '历史交易记录' }));

    expect(screen.getByTestId('location')).toHaveTextContent(
      '/investmentLedger/history|module-switch',
    );
    expect(screen.getByRole('menuitem', { name: '历史交易记录' })).toHaveClass(
      'ant-menu-item-selected',
    );
  });
});
