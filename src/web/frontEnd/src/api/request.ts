// api/request.ts
// 账本模块专用 axios 实例与错误归一，是本模块唯一的 HTTP 底座（api/ledger.ts 之下不再出现裸 axios）。
// 约定：响应体沿用项目既有 { code, msg, data } 信封（见 api/index.js 的 get()），
//      这里只是把该约定用泛型固化，并把「业务码错误 / HTTP 状态错误 / 网络异常」三类失败
//      统一归一为 LedgerApiError，使状态层的 catch 分支只需处理一种错误类型
//      （需求 1.2、2.20、2.21、2.26、2.30、3.2）。
import axios from 'axios';
import type { AxiosResponse } from 'axios';
import type { ApiEnvelope, FieldErrorItem } from './types';

/** 业务成功码：与后端 ApiResponse.code 的成功取值一致 */
export const SUCCESS_CODE = 200;

/** 账本模块接口前缀：与后端 APIRouter(prefix="/investmentLedger") 及 app/api.py 的 /api 前缀拼接而成 */
export const LEDGER_API_BASE_URL = '/api/investmentLedger';

/** 请求超时（毫秒）：超时后按网络异常处理，不让界面无限等待 */
export const LEDGER_API_TIMEOUT = 10000;

/** 网络不可达、超时、服务端 5xx 等「非业务」失败的统一中文提示 */
export const NETWORK_ERROR_MESSAGE = '网络异常，请稍后重试';

/** 无法从响应中取到中文提示时的兜底文案，保证 message 永不为空 */
export const UNKNOWN_ERROR_MESSAGE = '请求失败，请稍后重试';

/** 无 HTTP 响应（网络异常/超时/请求被取消）时使用的占位业务码 */
export const NETWORK_ERROR_CODE = 0;

/**
 * 账本模块统一异常类型：把网络错误、HTTP 状态错误、业务 code 错误收敛为同一形状，
 * 使 thunk 的 catch 分支只需处理一种错误类型。
 */
export class LedgerApiError extends Error {
  /**
   * @param message 面向用户的中文提示（恒为非空，必要时取兜底文案）
   * @param fieldErrors 字段级错误；仅 422 场景非空，其余为空数组（需求 1.2、3.2）
   * @param code 业务码：来自信封的 code，无响应时为 NETWORK_ERROR_CODE
   */
  constructor(
    message: string,
    readonly fieldErrors: FieldErrorItem[] = [],
    readonly code: number = NETWORK_ERROR_CODE
  ) {
    super(message || UNKNOWN_ERROR_MESSAGE);
    this.name = 'LedgerApiError';
    // 兼容按 ES5 语义降级的运行时，保证 instanceof LedgerApiError 成立
    Object.setPrototypeOf(this, LedgerApiError.prototype);
  }
}

/** 判定任意响应体是否为项目约定的 { code, msg, data } 信封 */
function isApiEnvelope(body: unknown): body is ApiEnvelope<unknown> {
  return (
    typeof body === 'object' &&
    body !== null &&
    typeof (body as { code?: unknown }).code === 'number' &&
    'data' in body
  );
}

/** 判定单个元素是否为可回填表单的字段错误项（字段名 + 错误码 + 中文原因） */
function isFieldErrorItem(item: unknown): item is FieldErrorItem {
  return (
    typeof item === 'object' &&
    item !== null &&
    typeof (item as { field?: unknown }).field === 'string' &&
    typeof (item as { message?: unknown }).message === 'string'
  );
}

/**
 * 从信封的 data 中提取字段级错误：后端 422 以 data.fieldErrors 携带（见 exceptions.py）。
 * 形状不符时返回空数组，绝不抛出，避免错误归一过程本身再产生异常。
 */
function extractFieldErrors(data: unknown): FieldErrorItem[] {
  if (typeof data !== 'object' || data === null) return [];
  const { fieldErrors } = data as { fieldErrors?: unknown };
  if (!Array.isArray(fieldErrors)) return [];
  return fieldErrors.filter(isFieldErrorItem);
}

/**
 * HTTP 状态码到中文提示的兜底映射：仅在响应体不是约定信封（如网关/代理返回 HTML）时使用。
 * @param status HTTP 状态码
 */
function messageByStatus(status: number): string {
  if (status >= 500) return NETWORK_ERROR_MESSAGE;
  if (status === 404) return '请求的数据不存在，请刷新后重试';
  if (status === 400 || status === 422) return '提交的数据不合法，请修正后重试';
  return UNKNOWN_ERROR_MESSAGE;
}

/**
 * 错误归一：任意异常 → LedgerApiError。
 * - 已是 LedgerApiError：原样返回（避免重复包装丢失 fieldErrors）
 * - 有 HTTP 响应且响应体为信封：保留后端的 code、中文 msg 与 fieldErrors（422 场景）
 * - 有 HTTP 响应但响应体非信封：按状态码取中文提示
 * - 无 HTTP 响应（网络异常、超时、取消）：统一为「网络异常，请稍后重试」
 * @param error 任意来源的异常
 */
export function normalizeError(error: unknown): LedgerApiError {
  if (error instanceof LedgerApiError) return error;

  if (axios.isAxiosError(error)) {
    const { response } = error;
    if (!response) {
      return new LedgerApiError(NETWORK_ERROR_MESSAGE, [], NETWORK_ERROR_CODE);
    }
    const body: unknown = response.data;
    if (isApiEnvelope(body)) {
      const msg = typeof body.msg === 'string' ? body.msg : '';
      return new LedgerApiError(
        msg || messageByStatus(response.status),
        extractFieldErrors(body.data),
        body.code
      );
    }
    return new LedgerApiError(messageByStatus(response.status), [], response.status);
  }

  return new LedgerApiError(NETWORK_ERROR_MESSAGE, [], NETWORK_ERROR_CODE);
}

/** axios 实例：baseURL 固定到本模块前缀，超时 10s 后按网络异常处理 */
const http = axios.create({ baseURL: LEDGER_API_BASE_URL, timeout: LEDGER_API_TIMEOUT });

// 响应拦截器：成功响应原样透传（信封解包交给 unwrap 的泛型出口统一处理），
// 失败响应在进入调用方之前就归一为 LedgerApiError，保证不会有裸 AxiosError 外泄。
http.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(normalizeError(error))
);

/**
 * 泛型解包：{ code, msg, data } → data。
 * @param promise 任一返回 ApiEnvelope<T> 的 axios 调用
 * @returns 成功时的业务负载 T（删除类接口的 T 为 null，此时如实返回 null）
 * @throws LedgerApiError code !== 200、HTTP 非 2xx、网络异常或超时
 * 不变量：调用方永远只需处理 T 与 LedgerApiError 两种结果，不需要再判 code
 */
export async function unwrap<T>(promise: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  let body: unknown;
  try {
    const response = await promise;
    body = response.data;
  } catch (error) {
    throw normalizeError(error);
  }

  if (!isApiEnvelope(body)) {
    throw new LedgerApiError(UNKNOWN_ERROR_MESSAGE);
  }

  const envelope = body as ApiEnvelope<T>;
  if (envelope.code !== SUCCESS_CODE) {
    throw new LedgerApiError(
      typeof envelope.msg === 'string' && envelope.msg ? envelope.msg : UNKNOWN_ERROR_MESSAGE,
      extractFieldErrors(envelope.data),
      envelope.code
    );
  }

  return envelope.data as T;
}

export default http;
