// domain/ledger/FundSearchController.ts
// 基金搜索控制器：封装 500ms 防抖、请求竞态保护与生命周期收尾（需求 5.3、5.6、5.8）。
//
// 设计要点：
//   1. 只暴露 search(keyword) 与 dispose() 两个方法，不接触 React、不接触 Redux，
//      使其可被 React.Component 在 componentDidMount/componentDidUpdate 中直接使用，
//      也便于在 Vitest 中用 fake timers + fake api 单独验证防抖与竞态行为。
//   2. 空 keyword（含纯空白）不发任何请求，立即回调空结果并清除加载态（需求 5.3）。
//   3. 每次发起请求递增 requestId；只有最新请求的结果会回调 onResults，
//      杜绝「慢请求覆盖快请求」的竞态错位（需求 5.6 的前端延伸保护）。
//   4. dispose() 取消挂起定时器并使所有在飞请求结果失效，避免组件卸载后 setState。
//   5. 网络/服务端异常由 api 层归一为 LedgerApiError；本控制器捕获后收敛为空结果，
//      不向上抛出，保证调用方（TradeFormModal）不会因搜索失败而抛未处理异常。
import { searchFunds } from '../../api/ledger';
import type { FundSearchOut } from '../../api/types';

/** FundSearchController 的回调集合：由 TradeFormModal 提供以接收结果与加载态 */
export interface FundSearchControllerCallbacks {
  /** 收到最新请求的结果；旧请求结果不会触发本回调 */
  readonly onResults: (results: readonly FundSearchOut[]) => void;
  /** 加载态变更回调；true 表示正在等待防抖或请求 */
  readonly onLoadingChange: (loading: boolean) => void;
}

/** 防抖延迟默认值（毫秒）；需求 5.3 规定为 500 毫秒 */
export const FUND_SEARCH_DEBOUNCE_MS = 500;

/**
 * 基金搜索控制器：防抖 + 竞态控制 + 请求出口。
 *
 * 不变量：
 * - 空 keyword 永不发起请求，且立即回调空结果（需求 5.3）；
 * - 仅最新一次有效请求的结果会回调 onResults；
 * - dispose 后不再回调任何结果，pending 请求结果被丢弃；
 * - 任何异常都被捕获并收敛为空结果，不向上抛出。
 */
export class FundSearchController {
  /** 挂起的防抖定时器；为 null 表示当前无挂起请求 */
  private timerId: ReturnType<typeof setTimeout> | null = null;
  /** 单调递增的请求标识；仅当回调到达时该值仍为最新，才认为结果有效 */
  private latestRequestId = 0;
  /** 是否已销毁；销毁后不再回调，避免组件卸载后 setState */
  private disposed = false;
  /** 当前是否处于加载态；用于在空 keyword 收敛时正确复位 */
  private loading = false;

  /**
   * @param callbacks 结果与加载态回调
   * @param debounceMs 防抖延迟毫秒数，默认 500（需求 5.3）
   */
  constructor(
    private readonly callbacks: FundSearchControllerCallbacks,
    private readonly debounceMs: number = FUND_SEARCH_DEBOUNCE_MS,
  ) {}

  /**
   * 调度一次防抖搜索。
   *
   * 空 keyword（含纯空白）取消挂起定时器、立即回调空结果并清除加载态，
   * 不发起任何请求（需求 5.3）。非空 keyword 取消上次定时器后重新计时，
   * 使连续输入只以最后一次为准。
   *
   * @param keyword 用户输入内容
   */
  public search(keyword: string): void {
    if (this.disposed) return;
    this.clearTimer();
    const trimmed = keyword.trim();
    if (trimmed.length === 0) {
      // 空 keyword：取消在飞请求（递增 requestId 使其结果失效）、立即收敛为空结果，
      // 用于输入清空、选中结果回填、弹窗关闭等需要丢弃挂起请求的场景
      this.latestRequestId += 1;
      this.applyResults([], /*loading*/ false);
      return;
    }
    // 进入「等待防抖」加载态，给用户即时反馈
    this.setLoading(true);
    this.timerId = setTimeout(() => {
      this.timerId = null;
      void this.runSearch(trimmed);
    }, this.debounceMs);
  }

  /**
   * 取消挂起的定时器并使所有在飞请求结果失效。
   *
   * 调用后该实例不再回调任何结果；TradeFormModal 卸载或切换为非基金类型时应调用。
   */
  public dispose(): void {
    this.disposed = true;
    this.clearTimer();
    // 使任何在飞请求结果失效：递增 latestRequestId 后其本地快照不再相等
    this.latestRequestId += 1;
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

  /** 统一应用结果并设置加载态；仅在未被更新的请求覆盖时生效。 */
  private applyResults(
    results: readonly FundSearchOut[],
    loading: boolean,
  ): void {
    if (this.disposed) return;
    this.loading = loading;
    this.callbacks.onLoadingChange(loading);
    this.callbacks.onResults(results);
  }

  /**
   * 执行一次搜索请求，并在仍是最新请求时回放结果。
   *
   * 任何异常被捕获并收敛为空结果，不向上抛出（需求 5.6 的前端延伸）。
   */
  private async runSearch(keyword: string): Promise<void> {
    const requestId = this.latestRequestId + 1;
    this.latestRequestId = requestId;
    try {
      const results = await searchFunds(keyword);
      // 仅当本次请求仍是最新请求时回放结果，避免竞态错位
      if (requestId !== this.latestRequestId || this.disposed) return;
      this.applyResults(results, false);
    } catch {
      // 网络/服务端异常收敛为空结果，加载态复位
      if (requestId !== this.latestRequestId || this.disposed) return;
      this.applyResults([], false);
    }
  }
}

export default FundSearchController;
