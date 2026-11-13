import type { RunStatus, TriggerKind } from './types';

export const STATUS_LABELS: Record<RunStatus, string> = {
    pending: '待执行',
    running: '运行中',
    success: '成功',
    failed: '失败',
    lost: '丢失',
    interrupted: '已中断',
    cancelled: '已取消',
};

export const STATUS_COLORS: Record<RunStatus, string> = {
    pending: 'blue',
    running: 'processing',
    success: 'green',
    failed: 'red',
    lost: 'magenta',
    interrupted: 'orange',
    cancelled: 'default',
};

export const TRIGGER_LABELS: Record<TriggerKind, string> = {
    schedule: '计划',
    catchup: '补跑',
    manual: '手动',
    retry: '重试',
};
