import ReactDOM from 'react-dom/client';
import React from 'react';
import { ConfigProvider } from 'antd';
// antd 的 locale 是 CommonJS 模块（exports.default = ...），在 webpack 的 ESM interop 下
// default import 可能拿到整个 module 对象而非真正的 locale 数据，导致 ConfigProvider 读不到
// Table.filterConfirm 等字段（表现为表格筛选「确定」按钮无文字、日期选择器不显示中文）。
// 这里显式兜底 .default，保证无论构建工具如何处理都取到真正的 locale 对象。
import zhCNLocale from 'antd/locale/zh_CN';
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

// 兼容 CommonJS default 导出：优先取 .default，取不到时回退到模块本身。
const zhCN = zhCNLocale.default || zhCNLocale;

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <ConfigProvider locale={zhCN}>
        <Provider store={store}>
            <RouterProvider router={router} />
        </Provider>
    </ConfigProvider>
);
