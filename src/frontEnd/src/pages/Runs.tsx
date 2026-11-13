import React, { useState } from 'react';
import {
    Alert,
    Button,
    Descriptions,
    Drawer,
    InputNumber,
    Modal,
    Select,
    Space,
    Table,
    Tag,
    message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import {
    cancelRun,
    cleanupRuns,
    errorMessage,
    fetchJobs,
    fetchRuns,
    retryRun,
} from '../api';
import { STATUS_COLORS, STATUS_LABELS, TRIGGER_LABELS } from '../constants';
import { usePolling } from '../hooks/usePolling';
import type { RunRecord, RunStatus } from '../types';

const STATUS_OPTIONS = (Object.keys(STATUS_LABELS) as RunStatus[]).map((value) => ({
    value,
    label: STATUS_LABELS[value],
}));

function formatTime(value: string | null): string {
    return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-';
}

export default function RunsPage() {
    const [messageApi, contextHolder] = message.useMessage();
    const [jobId, setJobId] = useState<string | undefined>(undefined);
    const [status, setStatus] = useState<RunStatus | undefined>(undefined);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [detail, setDetail] = useState<RunRecord | null>(null);
    const [cleanupOpen, setCleanupOpen] = useState(false);
    const [cleanupDays, setCleanupDays] = useState(30);

    const jobs = usePolling(fetchJobs, null);
    const { data, error, refresh } = usePolling(
        () => fetchRuns({ job_id: jobId, status, page, page_size: pageSize }),
        10000,
        [jobId, status, page, pageSize]
    );

    const jobOptions = (jobs.data ?? []).map((job) => ({
        value: job.id,
        label: `${job.name} (${job.id})`,
    }));

    const act = async (action: () => Promise<{ message?: string }>) => {
        try {
            const result = await action();
            messageApi.success(result.message ?? '操作成功');
            await refresh();
        } catch (err) {
            messageApi.error(errorMessage(err));
        }
    };

    const confirmCleanup = async () => {
        try {
            const result = await cleanupRuns(cleanupDays);
            messageApi.success(`已清理 ${result.removed ?? 0} 条记录`);
            setCleanupOpen(false);
            await refresh();
        } catch (err) {
            messageApi.error(errorMessage(err));
        }
    };

    const columns: ColumnsType<RunRecord> = [
        { title: '#', dataIndex: 'id', width: 80 },
        { title: '任务', dataIndex: 'job_id', width: 120 },
        {
            title: '计划时间',
            dataIndex: 'scheduled_at',
            width: 180,
            render: formatTime,
        },
        {
            title: '触发',
            dataIndex: 'trigger_kind',
            width: 90,
            render: (value: RunRecord['trigger_kind']) => TRIGGER_LABELS[value],
        },
        {
            title: '状态',
            dataIndex: 'status',
            width: 100,
            render: (value: RunStatus) => (
                <Tag color={STATUS_COLORS[value]}>{STATUS_LABELS[value]}</Tag>
            ),
        },
        {
            title: '尝试',
            width: 90,
            render: (_value, record) => `${record.attempt}/${record.max_attempts}`,
        },
        {
            title: '下次重试',
            dataIndex: 'next_retry_at',
            width: 180,
            render: formatTime,
        },
        {
            title: '错误',
            dataIndex: 'error',
            ellipsis: true,
            render: (value: string | null) => value ?? '-',
        },
        {
            title: '操作',
            width: 190,
            render: (_value, record) => (
                <Space size={0}>
                    <Button type="link" size="small" onClick={() => setDetail(record)}>
                        详情
                    </Button>
                    {record.status === 'failed' && (
                        <Button
                            type="link"
                            size="small"
                            onClick={() => act(() => retryRun(record.id))}
                        >
                            重试
                        </Button>
                    )}
                    {(record.status === 'pending' || record.status === 'interrupted') && (
                        <Button
                            type="link"
                            size="small"
                            danger
                            onClick={() => act(() => cancelRun(record.id))}
                        >
                            取消
                        </Button>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <>
            {contextHolder}
            <Space style={{ marginBottom: 16 }} wrap>
                <Select
                    allowClear
                    placeholder="按任务筛选"
                    style={{ width: 220 }}
                    options={jobOptions}
                    value={jobId}
                    onChange={(value) => {
                        setJobId(value);
                        setPage(1);
                    }}
                />
                <Select
                    allowClear
                    placeholder="按状态筛选"
                    style={{ width: 160 }}
                    options={STATUS_OPTIONS}
                    value={status}
                    onChange={(value) => {
                        setStatus(value);
                        setPage(1);
                    }}
                />
                <Button onClick={() => void refresh()}>刷新</Button>
                <Button onClick={() => setCleanupOpen(true)}>清理历史</Button>
            </Space>

            {error && (
                <Alert
                    type="error"
                    showIcon
                    message="加载运行记录失败"
                    description={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            <Table
                rowKey="id"
                dataSource={data?.items ?? []}
                columns={columns}
                loading={data === null}
                pagination={{
                    current: page,
                    pageSize,
                    total: data?.total ?? 0,
                    showSizeChanger: true,
                    pageSizeOptions: ['20', '50', '100'],
                    onChange: (nextPage, nextSize) => {
                        setPage(nextPage);
                        setPageSize(nextSize);
                    },
                }}
            />

            <Drawer
                title={detail ? `运行记录 #${detail.id}` : '运行记录'}
                width={520}
                open={detail !== null}
                onClose={() => setDetail(null)}
            >
                {detail && (
                    <Descriptions column={1} size="small">
                        <Descriptions.Item label="任务">{detail.job_id}</Descriptions.Item>
                        <Descriptions.Item label="触发类型">
                            {TRIGGER_LABELS[detail.trigger_kind]}
                        </Descriptions.Item>
                        <Descriptions.Item label="状态">
                            <Tag color={STATUS_COLORS[detail.status]}>
                                {STATUS_LABELS[detail.status]}
                            </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="计划时间">
                            {formatTime(detail.scheduled_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="开始时间">
                            {formatTime(detail.started_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="结束时间">
                            {formatTime(detail.finished_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="尝试次数">
                            {detail.attempt}/{detail.max_attempts}
                        </Descriptions.Item>
                        <Descriptions.Item label="错过次数">
                            {detail.missed_count}
                        </Descriptions.Item>
                        <Descriptions.Item label="下次重试">
                            {formatTime(detail.next_retry_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="告警时间">
                            {formatTime(detail.alerted_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="告警错误">
                            {detail.alert_error ?? '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="错误">
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                                {detail.error ?? '-'}
                            </pre>
                        </Descriptions.Item>
                    </Descriptions>
                )}
            </Drawer>

            <Modal
                title="清理历史记录"
                open={cleanupOpen}
                okText="清理"
                cancelText="取消"
                onOk={confirmCleanup}
                onCancel={() => setCleanupOpen(false)}
            >
                <p>仅删除早于保留期的终态记录，待执行、运行中、已中断与待重试记录会保留。</p>
                <Space>
                    保留天数
                    <InputNumber
                        min={1}
                        max={3650}
                        value={cleanupDays}
                        onChange={(value) => setCleanupDays(value ?? 30)}
                    />
                </Space>
            </Modal>
        </>
    );
}
