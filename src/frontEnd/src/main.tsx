import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCNLocale from 'antd/locale/zh_CN';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

import 'normalize.css';
import App from './App';

dayjs.locale('zh-cn');

// antd 的 locale 是 CommonJS 模块，webpack 的 ESM interop 下可能取到模块对象。
const zhCN = (zhCNLocale as unknown as { default?: typeof zhCNLocale }).default ?? zhCNLocale;

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <ConfigProvider locale={zhCN}>
        <App />
    </ConfigProvider>
);
