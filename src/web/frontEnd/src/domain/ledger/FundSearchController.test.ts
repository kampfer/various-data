// FundSearchController 的定向单元测试。
// 覆盖防抖、全局 r 的代码/拼音/中文名匹配、缺失数据降级与生命周期收尾。
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { FundSearchOut } from '../../api/types';
import { FundSearchController, FUND_SEARCH_DEBOUNCE_MS } from './FundSearchController';

interface CollectedState {
  results: FundSearchOut[][];
  loading: boolean[];
}

function createController(): { controller: FundSearchController; state: CollectedState } {
  const state: CollectedState = { results: [], loading: [] };
  const controller = new FundSearchController({
    onResults: (results) => void state.results.push([...results]),
    onLoadingChange: (loading) => void state.loading.push(loading),
  });
  return { controller, state };
}

describe('FundSearchController', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.r = [
      ['005827', 'YFDLCJXHH', '易方达蓝筹精选混合'],
      ['110022', 'YFDCF', '易方达消费行业股票'],
      ['000001', 'HXCZZZ', '华夏成长证券'],
    ];
  });

  afterEach(() => {
    window.r = undefined;
    vi.useRealTimers();
  });

  it('连续输入只以最后一次关键词筛选，500ms 内不筛选', () => {
    const { controller, state } = createController();

    controller.search('易');
    controller.search('易方');
    controller.search('易方达');

    expect(state.results).toEqual([]);
    expect(state.loading).toEqual([true]);

    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS - 1);
    expect(state.results).toEqual([]);

    vi.advanceTimersByTime(1);
    expect(state.results).toEqual([[
      { fundName: '易方达蓝筹精选混合', fundCode: '005827' },
      { fundName: '易方达消费行业股票', fundCode: '110022' },
    ]]);
  });

  it('支持以基金代码、拼音缩写或中文名筛选', () => {
    const expectations: Array<[string, FundSearchOut[]]> = [
      ['5827', [{ fundName: '易方达蓝筹精选混合', fundCode: '005827' }]],
      ['yfdlc', [{ fundName: '易方达蓝筹精选混合', fundCode: '005827' }]],
      ['华夏', [{ fundName: '华夏成长证券', fundCode: '000001' }]],
    ];

    for (const [keyword, expectedResults] of expectations) {
      const { controller, state } = createController();
      controller.search(keyword);
      vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS);
      expect(state.results).toEqual([expectedResults]);
    }
  });

  it('空 keyword 不筛选并立即清空结果与加载态', () => {
    const { controller, state } = createController();
    controller.search('');

    expect(state.results).toEqual([[]]);
    expect(state.loading[state.loading.length - 1]).toBe(false);
  });

  it('全局 r 缺失或记录不合法时安全返回空结果', () => {
    window.r = undefined;
    const { controller, state } = createController();
    controller.search('易方达');
    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS);

    expect(state.results).toEqual([[]]);
  });

  it('dispose 后挂起定时器不再筛选或回调结果', () => {
    const { controller, state } = createController();
    controller.search('易方达');
    controller.dispose();

    vi.advanceTimersByTime(FUND_SEARCH_DEBOUNCE_MS * 2);
    expect(state.results).toEqual([]);
  });
});
