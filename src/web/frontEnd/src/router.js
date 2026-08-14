import React from 'react';
import {
  createHashRouter,
} from 'react-router-dom';
import ChartWithNews from './pages/ChartWithNews/index.js';
import CrawlersAdmin from './pages/CrawlersAdmin.js';
import Home from './pages/Home.js';
import InvestmentLedger from './pages/InvestmentLedger/index';

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
    element: <InvestmentLedger />
  },
  {
    path: '/',
    element: <Home />
  }
]);

export default router;
