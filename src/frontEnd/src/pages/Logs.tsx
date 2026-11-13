import React, { useState } from 'react';
import { Alert, Button, Select, Space, Switch, Typography } from 'antd';

import { fetchLogs } from '../api';
import { usePolling } from '../hooks/usePolling';

const LINE_OPTIONS = [200, 500, 1000, 2000].map((value) => ({
    value,
    label: `最近 ${value} 行`,
}));

export default function LogsPage() {
    const [lines, setLines] = useState(200);
    const [auto, setAuto] = useState(false);
    const { data, error, refresh } = usePolling(
        () => fetchLogs(lines),
        auto ? 5000 : null,
        [lines]
    );

    return (
        <>
            <Space style={{ marginBottom: 16 }} wrap>
                <Select
                    options={LINE_OPTIONS}
                    value={lines}
                    style={{ width: 160 }}
                    onChange={(value) => setLines(value)}
                />
                <Button onClick={() => void refresh()}>刷新</Button>
                <Space>
                    自动刷新
                    <Switch checked={auto} onChange={setAuto} />
                </Space>
                {data?.truncated && (
                    <Typography.Text type="warning">
                        已按上限 {data.limit} 行截断
                    </Typography.Text>
                )}
            </Space>

            {error && (
                <Alert
                    type="error"
                    showIcon
                    message="加载日志失败"
                    description={error}
                    style={{ marginBottom: 16 }}
                />
            )}
            {data?.error && (
                <Alert
                    type="warning"
                    showIcon
                    message={data.error}
                    description={`日志路径：${data.path}`}
                    style={{ marginBottom: 16 }}
                />
            )}

            <pre
                style={{
                    margin: 0,
                    padding: 16,
                    background: '#141414',
                    color: '#d9d9d9',
                    borderRadius: 8,
                    maxHeight: 'calc(100vh - 260px)',
                    overflow: 'auto',
                    fontSize: 12,
                    lineHeight: 1.6,
                }}
            >
                {data?.lines.length ? data.lines.join('\n') : '暂无日志'}
            </pre>
        </>
    );
}
