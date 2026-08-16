// 通信层示例单元测试：任务 11.4；通过 axios adapter 隔离真实网络。
// Validates: Requirements 1.2, 2.16, 2.17, 2.18
import { afterEach, describe, expect, it } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import LedgerQueryState from '../domain/ledger/LedgerQueryState';
import { fetchTransactions } from './ledger';
import http, {
  LedgerApiError,
  NETWORK_ERROR_CODE,
  NETWORK_ERROR_MESSAGE,
  unwrap,
} from './request';
import type { ApiEnvelope, FieldErrorItem, PageOut, TransactionOut } from './types';

const originalAdapter = http.defaults.adapter;

/** 构造不经过网络的 axios 响应。 */
function response<T>(data: ApiEnvelope<T>, status = 200): AxiosResponse<ApiEnvelope<T>> {
  return {
    data,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() } as InternalAxiosRequestConfig,
  };
}

/** 构造带 HTTP 响应的 AxiosError，供错误归一入口消费。 */
function responseError<T>(status: number, data: ApiEnvelope<T>): AxiosError<ApiEnvelope<T>> {
  const axiosResponse = response(data, status);
  return new AxiosError(
    `Request failed with status code ${status}`,
    AxiosError.ERR_BAD_REQUEST,
    axiosResponse.config,
    undefined,
    axiosResponse,
  );
}

/** 取得 promise 抛出的统一账本错误，并验证不会泄漏裸异常。 */
async function captureLedgerError(promise: Promise<unknown>): Promise<LedgerApiError> {
  try {
    await promise;
    throw new Error('预期请求失败，但请求成功');
  } catch (error) {
    expect(error).toBeInstanceOf(LedgerApiError);
    return error as LedgerApiError;
  }
}

afterEach(() => {
  http.defaults.adapter = originalAdapter;
});

describe('通信层错误归一', () => {
  it('将业务错误归一为保留业务码和中文提示的 LedgerApiError', async () => {
    const error = await captureLedgerError(
      unwrap(Promise.resolve(response({ code: 409, msg: '交易记录状态已变化，请刷新后重试', data: null }))),
    );

    expect(error).toMatchObject({
      name: 'LedgerApiError',
      code: 409,
      message: '交易记录状态已变化，请刷新后重试',
      fieldErrors: [],
    });
    expect(error.message).toMatch(/[\u4e00-\u9fa5]/);
  });

  it('将 422 响应归一为携带中文字段提示的 LedgerApiError', async () => {
    const fieldErrors: FieldErrorItem[] = [
      { field: 'productType', code: 'NOT_IN_ENUM', message: '产品类型必须为理财、基金或股票之一' },
      { field: 'transactionPrice', code: 'NOT_A_NUMBER', message: '交易价格必须是有限十进制数值' },
    ];
    const error = await captureLedgerError(
      unwrap(Promise.reject(responseError(422, {
        code: 422,
        msg: '提交的数据不合法，请修正后重试',
        data: { fieldErrors },
      }))),
    );

    expect(error).toMatchObject({ code: 422, message: '提交的数据不合法，请修正后重试' });
    expect(error.fieldErrors).toEqual(fieldErrors);
    error.fieldErrors.forEach(({ message }) => expect(message).toMatch(/[\u4e00-\u9fa5]/));
  });

  it('将无响应的网络异常归一为带统一中文提示的 LedgerApiError', async () => {
    const networkError = new AxiosError('Network Error', AxiosError.ERR_NETWORK);
    const error = await captureLedgerError(unwrap(Promise.reject(networkError)));

    expect(error).toMatchObject({
      code: NETWORK_ERROR_CODE,
      message: NETWORK_ERROR_MESSAGE,
      fieldErrors: [],
    });
    expect(error.message).toMatch(/[\u4e00-\u9fa5]/);
  });
});

describe('账本查询请求参数', () => {
  const emptyPage: PageOut<TransactionOut> = {
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
    pageCount: 0,
  };

  it.each([
    {
      name: '仅启用筛选和产品名称搜索',
      query: LedgerQueryState.default('history').withFilters({
        productType: 'FUND',
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        productName: '指数基金',
      }),
      expected: {
        productType: 'FUND',
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        productName: '指数基金',
        page: 1,
        pageSize: 20,
      },
    },
    {
      name: '同时启用产品名称和产品代码搜索',
      query: LedgerQueryState.default('history').withFilters({
        productName: '沪深300',
        productCode: '510300',
      }),
      expected: { productName: '沪深300', productCode: '510300', page: 1, pageSize: 20 },
    },
  ])('$name 时只发送已启用条件', async ({ query, expected }) => {
    let sentConfig: InternalAxiosRequestConfig | undefined;
    http.defaults.adapter = async (config) => {
      sentConfig = config;
      return response({ code: 200, msg: '查询成功', data: emptyPage });
    };

    await expect(fetchTransactions(query.toParams())).resolves.toEqual(emptyPage);

    expect(sentConfig?.url).toBe('/transactions');
    expect(sentConfig?.params).toEqual(expected);
    expect(Object.values(sentConfig?.params ?? {})).not.toContain(null);
  });
});