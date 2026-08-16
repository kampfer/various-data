import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchInitialModule } from '../../api/ledger';
import IndexRedirect from './IndexRedirect';

vi.mock('../../api/ledger', () => ({
  fetchInitialModule: vi.fn(),
}));

const mockedFetchInitialModule = vi.mocked(fetchInitialModule);

const renderRedirect = () => render(
  <MemoryRouter initialEntries={['/investmentLedger']}>
    <Routes>
      <Route path="/investmentLedger" element={<IndexRedirect />} />
      <Route path="/investmentLedger/:module" element={<div data-testid="target">目标模块</div>} />
    </Routes>
  </MemoryRouter>,
);

describe('IndexRedirect', () => {
  beforeEach(() => {
    mockedFetchInitialModule.mockReset();
  });

  it('无交易时调用初始模块接口并替换到 history', async () => {
    mockedFetchInitialModule.mockResolvedValue({ module: 'history' });
    renderRedirect();

    await waitFor(() => expect(screen.getByTestId('target')).toBeInTheDocument());
    expect(mockedFetchInitialModule).toHaveBeenCalledOnce();
  });

  it('存在交易时调用初始模块接口并替换到 holdings', async () => {
    mockedFetchInitialModule.mockResolvedValue({ module: 'holdings' });
    renderRedirect();

    await waitFor(() => expect(screen.getByTestId('target')).toBeInTheDocument());
    expect(mockedFetchInitialModule).toHaveBeenCalledOnce();
  });
});
