import React from 'react';
import {
  createHashRouter,
} from 'react-router-dom';
import ChartWithNews from './pages/ChartWithNews/index.js';
import CrawlersAdmin from './pages/CrawlersAdmin.js';
import Home from './pages/Home.js';
import LedgerLayout from './pages/InvestmentLedger/index';
import IndexRedirect from './pages/InvestmentLedger/IndexRedirect';
import HoldingsPage from './pages/InvestmentLedger/HoldingsPage';
import HistoryPage from './pages/InvestmentLedger/HistoryPage';

const router = createHashRouter([
  {
    path: '/chartWithNews',
    element: <ChartWithNews />,
  },
  {
    path: '/crawlersAdmin',
    element: <CrawlersAdmin />
  },
  {
    path: '/investmentLedger',
    element: <LedgerLayout />,
    children: [
      { index: true, element: <IndexRedirect /> },
      { path: 'holdings', element: <HoldingsPage /> },
      { path: 'history', element: <HistoryPage /> },
    ],
  },
  {
    path: '/',
    element: <Home />
  }
]);

export default router;
