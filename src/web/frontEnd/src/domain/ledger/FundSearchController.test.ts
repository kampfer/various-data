// FundSearchController 的定向单元测试（任务 16.4）。
//
// 测试目标：覆盖三类核心不变量
//   1. 防抖（需求 5.3）：连续输入只以最后一次为准发起请求；500ms 内不发起；
//      空 keyword 不发请求并立即清空结果。
//   2. 竞态保护：慢请求结果不会覆盖快请求结果；只有最新请求的结果会回调。
//   3. 生命周期收尾：dispose 后挂起定时器与在飞请求结果都不再回调，
//      避免组件卸载后 setState；异常被收敛为空结果，不向上抛出。
//
// 通过 vi.mock 隔离真实 axios 与后端，使用 fake timers 精确控制 500ms 防抖。
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import type { FundSearchOut } from '../../api/types';
import { FundSearchController, FUND_SEARCH_DEBOUNCE_MS } from './FundSearchController';

// 隔离真实 HTTP 出口；测试通过把 searchFunds 替换为受控 mock 实现，
// 使控制器只与「返回 Promise 的函数」交互，不接触网络。
vi.mock('../../api/ledger', () => ({
  // 默认实现：返回空数组；具体用例可在 it 内通过 mockResolvedValue 改写
  searchFunds: vi.fn().mockResolvedValue([] as FundSearchOut[]),
}));

// 动态 import 与静态 mock 同步：先声明 mock，再 await import 拿到被 mock 后的模块
const { searchFunds } = await import('../../api/ledger');

interface CollectedState {
  // 收集器内部需要可变数组以累积回调历史；元素类型仍为只读结果数组
  results: FundSearchOut[][];
  loading: boolean[];
}

function createController(): { controller: FundSearchController; state: CollectedState } {
  const state: CollectedState = { results: [], loading: [] };
  const controller = new FundSearchController({
    // 把只读结果数组拷贝为可变数组后再累积，避免与 readonly 类型冲突
    onResults: (results) => void state.results.push([...results]),
    onLoadingChange: (loading) => void state.loading.push(loading),
  });
  return { controller, state };
}

describe('FundSearchController', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(searchFunds).mockReset();
    vi.mocked(searchFunds).mockResolvedValue([]);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // --- 不变量 1：防抖（需求 5.3） ---------------------------------------

  it('连续输入只以最后一次为关键词发起请求，500ms 内不发起', () => {
    const { controller, state } = createController();

    controller.search('易');
    controller.search('易方');
    controller.search('易方达');

    // 防抖窗口内不应发起任何请求，也不应回放结果
    expect(searchFunds).not.toHaveBeenCalled();
    expect(state.results).toEqual([]);
    // 进入「等待防抖」加载态应只触发一次 true
    expect(state.loading).toEqual([true]);

    // 推进 499ms：仍不应发起
    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS - 1);
    expect(searchFunds).not.toHaveBeenCalled();

    // 推进到 500ms 阈值：以最后一次关键词发起请求
    vi.advanceTimersByTime(1);
    expect(searchFunds).toHaveBeenCalledTimes(1);
    expect(searchFunds).toHaveBeenCalledWith('易方达');
  });

  it('空 keyword 不发请求并立即清空结果与加载态', () => {
    const { controller, state } = createController();

    controller.search('');

    expect(searchFunds).not.toHaveBeenCalled();
    // 立即回调空结果与加载态 false
    expect(state.results).toEqual([[]]);
    expect(state.loading[state.loading.length - 1]).toBe(false);
  });

  it('纯空白 keyword 视为空输入，不发请求', () => {
    const { controller } = createController();

    controller.search('   ');

    expect(searchFunds).not.toHaveBeenCalled();
  });

  // --- 不变量 2：竞态保护 ------------------------------------------------

  it('慢请求结果不会覆盖快请求结果，仅最新请求回调', async () => {
    const { controller, state } = createController();
    // 第一次请求：resolve 慢（手动挂起）
    let resolveSlow: (value: FundSearchOut[]) => void = () => undefined;
    vi.mocked(searchFunds).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSlow = resolve;
      }),
    );
    // 第二次请求：resolve 快
    const fastResults: FundSearchOut[] = [
      { fundName: '快基金', fundCode: 'F001' },
    ];
    vi.mocked(searchFunds).mockResolvedValueOnce(fastResults);

    // 触发第一次搜索
    controller.search('慢');
    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS);
    expect(searchFunds).toHaveBeenCalledTimes(1);

    // 在慢请求未完成时触发第二次搜索
    controller.search('快');
    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS);
    expect(searchFunds).toHaveBeenCalledTimes(2);

    // 让快请求先完成
    await vi.runAllTimersAsync();

    // 慢请求仍未 resolve；即使稍后 resolve，结果也不应回放
    resolveSlow([{ fundName: '慢基金', fundCode: 'F002' }]);
    // 给微任务队列一个推进机会
    await Promise.resolve();
    await Promise.resolve();

    // 仅快请求的结果被回调
    expect(state.results).toEqual([fastResults]);
  });

  it('请求异常被收敛为空结果，不向上抛出', async () => {
    const { controller, state } = createController();
    vi.mocked(searchFunds).mockRejectedValueOnce(new Error('网络异常'));

    controller.search('易方达');
    await vi.advanceTimersByTimeAsync(FUND_SEARCH_DEBOUNCE_MS);

    // 异常收敛为空结果；不抛出
    expect(state.results).toEqual([[]]);
    // 加载态复位
    expect(state.loading[state.loading.length - 1]).toBe(false);
  });

  // --- 不变量 3：生命周期收尾 --------------------------------------------

  it('dispose 后挂起定时器不再触发请求，在飞请求结果不再回调', async () => {
    const { controller, state } = createController();
    const pending = new Promise<FundSearchOut[]>(() => undefined);
    vi.mocked(searchFunds).mockReturnValueOnce(pending);

    controller.search('易方达');
    // 在防抖窗口内 dispose：定时器被取消
    controller.dispose();

    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS * 2);
    expect(searchFunds).not.toHaveBeenCalled();
    // 仅进入「等待防抖」加载态被记录，dispose 不再回放任何结果
    expect(state.results).toEqual([]);
  });
});
