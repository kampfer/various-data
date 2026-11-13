import React from 'react';
import { Layout, Tabs, Typography } from 'antd';

import JobsPage from './pages/Jobs';
import LogsPage from './pages/Logs';
import OverviewPage from './pages/Overview';
import RunsPage from './pages/Runs';

export default function App() {
    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Layout.Header
                style={{
                    background: '#fff',
                    borderBottom: '1px solid #f0f0f0',
                    display: 'flex',
                    alignItems: 'center',
                    paddingInline: 24,
                }}
            >
                <Typography.Title level={4} style={{ margin: 0 }}>
                    调度器后台管理
                </Typography.Title>
            </Layout.Header>
            <Layout.Content style={{ padding: 24 }}>
                <Tabs
                    items={[
                        { key: 'overview', label: '概览', children: <OverviewPage /> },
                        { key: 'jobs', label: '任务', children: <JobsPage /> },
                        { key: 'runs', label: '运行记录', children: <RunsPage /> },
                        { key: 'logs', label: '日志', children: <LogsPage /> },
                    ]}
                />
            </Layout.Content>
        </Layout>
    );
}
