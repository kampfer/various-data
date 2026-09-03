import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { searchFundResults } from './fundSearch';

describe('searchFundResults', () => {
  beforeEach(() => {
    window.r = [
      ['005827', 'YFDLCJXHH', '易方达蓝筹精选混合'],
      ['110022', 'YFDCF', '易方达消费行业股票'],
      ['000001', 'HXCZZZ', '华夏成长证券'],
    ];
  });

  afterEach(() => {
    window.r = undefined;
  });

  it.each([
    ['基金代码', '5827', [{ fundName: '易方达蓝筹精选混合', fundCode: '005827' }]],
    ['拼音缩写', 'yfdlc', [{ fundName: '易方达蓝筹精选混合', fundCode: '005827' }]],
    ['中文名称', '华夏', [{ fundName: '华夏成长证券', fundCode: '000001' }]],
  ])('按%s直接筛选全局 r', (_field, keyword, expectedResults) => {
    expect(searchFundResults(keyword)).toEqual(expectedResults);
  });

  it('r 未加载、记录不合法或关键词为空时返回空数组', () => {
    expect(searchFundResults('')).toEqual([]);

    window.r = undefined;
    expect(searchFundResults('易方达')).toEqual([]);
  });
});
