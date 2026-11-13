export type RunStatus =
    | 'pending'
    | 'running'
    | 'success'
    | 'failed'
    | 'lost'
    | 'interrupted'
    | 'cancelled';

export type TriggerKind = 'schedule' | 'catchup' | 'manual' | 'retry';

export interface AdminInfo {
    enabled: boolean;
    host: string;
    port: number;
}

export interface Overview {
    mode: string;
    db_path: string;
    ledger_path: string;
    started_at: string;
    admin: AdminInfo;
    today_start: string;
    pending: number;
    running: number;
    retrying: number;
    success_today: number;
    failed_today: number;
}

export interface RunRecord {
    id: number;
    job_id: string;
    scheduled_at: string;
    trigger_kind: TriggerKind;
    status: RunStatus;
    attempt: number;
    max_attempts: number;
    missed_count: number;
    next_retry_at: string | null;
    started_at: string | null;
    finished_at: string | null;
    error: string | null;
    alerted_at: string | null;
    alert_error: string | null;
    created_at: string;
}

export interface JobItem {
    id: string;
    name: string;
    cron: Record<string, number | string>;
    cron_text: string;
    catchup: 'backfill' | 'none';
    max_attempts: number;
    retry_interval_seconds: number;
    next_run_at: string | null;
    watermark: string | null;
    last_run: RunRecord | null;
}

export interface RunsResponse {
    total: number;
    page: number;
    page_size: number;
    items: RunRecord[];
    statuses: RunStatus[];
}

export interface LogsResponse {
    path: string;
    requested: number;
    limit: number;
    count: number;
    truncated: boolean;
    lines: string[];
    error: string | null;
}

export interface ActionResponse {
    ok?: boolean;
    created?: boolean;
    run_id?: number | null;
    removed?: number;
    cutoff?: string;
    message?: string;
}
