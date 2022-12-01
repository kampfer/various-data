import React from 'react';
import {
  createHashRouter,
} from 'react-router-dom';
import ChartWithNews from './pages/ChartWithNews/index.js';
import CrawlersAdmin from './pages/CrawlersAdmin.js';

const router = createHashRouter([
  {
    path: '/chartWithNews',
    element: <ChartWithNews />,
  },
  {
    path: '/crawlersAdmin',
    element: <CrawlersAdmin />
  }
]);

export default router;
