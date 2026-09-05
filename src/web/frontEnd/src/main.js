import ReactDOM from 'react-dom/client';
import React from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';
import { Provider } from 'react-redux';
import store from './store';
import router from './router.js';
import {
    RouterProvider,
} from 'react-router-dom';

import 'normalize.css';
import './main.css';

// 设置 Day.js 的全局语言，保证日期面板中的月份、星期等内容使用中文。
dayjs.locale('zh-cn');

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <ConfigProvider locale={zhCN}>
        <Provider store={store}>
            <RouterProvider router={router} />
        </Provider>
    </ConfigProvider>
);
