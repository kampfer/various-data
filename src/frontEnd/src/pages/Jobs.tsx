import React from 'react';
import { Alert, Button, Popconfirm, Space, Table, Tag, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { errorMessage, fetchJobs, runJob } from '../api';
import { STATUS_COLORS, STATUS_LABELS } from '../constants';
import { usePolling } from '../hooks/usePolling';
import type { JobItem } from '../types';

function formatTime(value: string | null): string {
    return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

export default function JobsPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const { data, error, refresh } = usePolling(fetchJobs, 10000);

    const trigger = async (jobId: string) => {
        try {
            const result = await runJob(jobId);
            messageApi.success(result.message ?? '已提交');
            await refresh();
        } catch (err) {
            messageApi.error(errorMessage(err));
        }
    };

    const columns: ColumnsType<JobItem> = [
        {
            title: '任务',
            dataIndex: 'name',
            render: (_value, record) => (
                <Space direction="vertical" size={0}>
                    <span>{record.name}</span>
                    <span style={{ color: '#999', fontSize: 12 }}>{record.id}</span>
                </Space>
            ),
        },
        {
            title: '周期',
            dataIndex: 'cron_text',
            render: (_value, record) => (
                <Space direction="vertical" size={0}>
                    <span>{record.cron_text}</span>
                    <span style={{ color: '#999', fontSize: 12 }}>
                        {JSON.stringify(record.cron)}
                    </span>
                </Space>
            ),
        },
        {
            title: '可补属性',
            dataIndex: 'catchup',
            render: (value: JobItem['catchup']) => (
                <Tag color={value === 'backfill' ? 'green' : 'orange'}>
                    {value === 'backfill' ? '可回溯' : '不可回溯'}
                </Tag>
            ),
        },
        {
            title: '重试',
            render: (_value, record) =>
                `${record.max_attempts} 次 / ${record.retry_interval_seconds} 秒`,
        },
        {
            title: '下次触发',
            dataIndex: 'next_run_at',
            render: formatTime,
        },
        {
            title: '触发水位',
            dataIndex: 'watermark',
            render: formatTime,
        },
        {
            title: '最近一次',
            render: (_value, record) => {
                if (!record.last_run) {
                    return '无记录';
                }
                const run = record.last_run;
                return (
                    <Space direction="vertical" size={0}>
                        <Tag color={STATUS_COLORS[run.status]}>{STATUS_LABELS[run.status]}</Tag>
                        <span style={{ fontSize: 12, color: '#999' }}>
                            {formatTime(run.finished_at ?? run.scheduled_at)}
                        </span>
                    </Space>
                );
            },
        },
        {
            title: '操作',
            render: (_value, record) => (
                <Popconfirm
                    title="立即执行该任务？"
                    description="会写入一条手动触发记录，由消费者串行执行。"
                    okText="执行"
                    cancelText="取消"
                    onConfirm={() => trigger(record.id)}
                >
                    <Button type="link" size="small">
                        立即执行
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    if (error) {
        return <Alert type="error" showIcon message="加载任务失败" description={error} />;
    }

    return (
        <>
            {contextHolder}
            <Table
                rowKey="id"
                dataSource={data ?? []}
                columns={columns}
                pagination={false}
                loading={data === null}
            />
        </>
    );
}
