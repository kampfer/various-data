// domain/ledger/FundSearchController.ts
// 基金搜索控制器：封装 500ms 防抖与生命周期收尾。
//
// 基金数据由 FundSearchResults/fundSearch 直接从 index.html 预加载的全局 r 读取；
// 本控制器不发起任何 HTTP 请求。
import { searchFundResults } from '../../components/InvestmentLedger/FundSearchResults/fundSearch';
import type { FundSearchOut } from '../../api/types';

/** FundSearchController 的回调集合：由 TradeFormModal 提供以接收结果与加载态 */
export interface FundSearchControllerCallbacks {
  /** 收到当前关键词的本地筛选结果。 */
  readonly onResults: (results: readonly FundSearchOut[]) => void;
  /** 加载态变更回调；true 表示正在等待防抖。 */
  readonly onLoadingChange: (loading: boolean) => void;
}

/** 防抖延迟默认值（毫秒）。 */
export const FUND_SEARCH_DEBOUNCE_MS = 500;

/**
 * 基金搜索控制器：防抖 + 生命周期管理。
 *
 * 不变量：
 * - 空 keyword 永不筛选，且立即回调空结果；
 * - 搜索结果由 FundSearchResults/fundSearch 从预加载的全局 r 读取；
 * - dispose 后不再回调任何结果。
 */
export class FundSearchController {
  /** 挂起的防抖定时器；为 null 表示当前无挂起筛选。 */
  private timerId: ReturnType<typeof setTimeout> | null = null;
  /** 是否已销毁；销毁后不再回调，避免组件卸载后 setState。 */
  private disposed = false;
  /** 当前是否处于加载态；用于在空 keyword 收敛时正确复位。 */
  private loading = false;

  /**
   * @param callbacks 结果与加载态回调
   * @param debounceMs 防抖延迟毫秒数，默认 500
   */
  constructor(
    private readonly callbacks: FundSearchControllerCallbacks,
    private readonly debounceMs: number = FUND_SEARCH_DEBOUNCE_MS,
  ) {}

  /** 调度一次本地基金代码表筛选。 */
  public search(keyword: string): void {
    if (this.disposed) return;
    this.clearTimer();
    const trimmed = keyword.trim();
    if (trimmed.length === 0) {
      this.applyResults([], false);
      return;
    }

    this.setLoading(true);
    this.timerId = setTimeout(() => {
      this.timerId = null;
      this.applyResults(searchFundResults(trimmed), false);
    }, this.debounceMs);
  }

  /** 取消挂起筛选并禁止后续回调。 */
  public dispose(): void {
    this.disposed = true;
    this.clearTimer();
    this.loading = false;
  }

  /** 清除挂起的防抖定时器（若存在）。 */
  private clearTimer(): void {
    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  }

  /** 统一设置加载态并回调；仅在状态变化时回调，避免冗余渲染。 */
  private setLoading(loading: boolean): void {
    if (this.loading === loading) return;
    this.loading = loading;
    this.callbacks.onLoadingChange(loading);
  }

  /** 统一应用结果并设置加载态。 */
  private applyResults(results: readonly FundSearchOut[], loading: boolean): void {
    if (this.disposed) return;
    this.loading = loading;
    this.callbacks.onLoadingChange(loading);
    this.callbacks.onResults(results);
  }
}

export default FundSearchController;
