import axios from 'axios';

import type {
    ActionResponse,
    JobItem,
    LogsResponse,
    Overview,
    RunsResponse,
} from './types';

const client = axios.create({ baseURL: '/api', timeout: 15000 });

export function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === 'string') {
            return detail;
        }
        return error.message;
    }
    return String(error);
}

export function fetchOverview(): Promise<Overview> {
    return client.get<Overview>('/overview').then((response) => response.data);
}

export function fetchJobs(): Promise<JobItem[]> {
    return client.get<JobItem[]>('/jobs').then((response) => response.data);
}

export function fetchRuns(params: {
    job_id?: string;
    status?: string;
    page: number;
    page_size: number;
}): Promise<RunsResponse> {
    return client.get<RunsResponse>('/runs', { params }).then((response) => response.data);
}

export function fetchLogs(lines: number): Promise<LogsResponse> {
    return client
        .get<LogsResponse>('/logs', { params: { lines } })
        .then((response) => response.data);
}

export function runJob(jobId: string): Promise<ActionResponse> {
    return client
        .post<ActionResponse>(`/jobs/${jobId}/run`)
        .then((response) => response.data);
}

export function retryRun(runId: number): Promise<ActionResponse> {
    return client
        .post<ActionResponse>(`/runs/${runId}/retry`)
        .then((response) => response.data);
}

export function cancelRun(runId: number): Promise<ActionResponse> {
    return client
        .post<ActionResponse>(`/runs/${runId}/cancel`)
        .then((response) => response.data);
}

export function cleanupRuns(days: number): Promise<ActionResponse> {
    return client
        .post<ActionResponse>('/runs/cleanup', { days })
        .then((response) => response.data);
}
