import React from 'react';
import { Alert, Card, Col, Descriptions, Row, Statistic } from 'antd';

import { fetchOverview } from '../api';
import { usePolling } from '../hooks/usePolling';

export default function OverviewPage() {
    const { data, error } = usePolling(fetchOverview, 5000);

    if (error) {
        return <Alert type="error" showIcon message="加载概览失败" description={error} />;
    }
    if (!data) {
        return <Card loading />;
    }

    return (
        <Row gutter={[16, 16]}>
            <Col span={6}>
                <Card>
                    <Statistic title="待执行" value={data.pending} />
                </Card>
            </Col>
            <Col span={6}>
                <Card>
                    <Statistic title="待重试" value={data.retrying} />
                </Card>
            </Col>
            <Col span={6}>
                <Card>
                    <Statistic title="今日成功" value={data.success_today} />
                </Card>
            </Col>
            <Col span={6}>
                <Card>
                    <Statistic title="今日失败" value={data.failed_today} />
                </Card>
            </Col>
            <Col span={24}>
                <Card title="运行环境">
                    <Descriptions column={2} size="small">
                        <Descriptions.Item label="模式">{data.mode}</Descriptions.Item>
                        <Descriptions.Item label="运行中">{data.running}</Descriptions.Item>
                        <Descriptions.Item label="业务库">{data.db_path}</Descriptions.Item>
                        <Descriptions.Item label="账本">{data.ledger_path}</Descriptions.Item>
                        <Descriptions.Item label="进程启动时间">
                            {data.started_at}
                        </Descriptions.Item>
                        <Descriptions.Item label="管理服务">
                            {data.admin.enabled
                                ? `${data.admin.host}:${data.admin.port}`
                                : '已关闭'}
                        </Descriptions.Item>
                    </Descriptions>
                </Card>
            </Col>
        </Row>
    );
}
