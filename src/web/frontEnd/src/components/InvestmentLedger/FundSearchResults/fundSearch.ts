import type { FundSearchOut } from '../../../api/types';

/**
 * 直接从 FundCode_utf8.js 注入的全局 r 中按基金代码查找基金。
 *
 * 每条记录依次为 [基金代码、基金名称拼音缩写、基金中文名]。本模块不请求
 * 后端或第三方接口；r 未加载、结构异常或没有匹配项时统一返回空数组。
 */
export const searchFundResults = (keyword: string): FundSearchOut[] => {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase();
  if (normalizedKeyword.length === 0 || !Array.isArray(window.r)) return [];

  return window.r.reduce<FundSearchOut[]>((results, record) => {
    if (!Array.isArray(record)) return results;
    const [fundCode, , fundName] = record;
    if (typeof fundCode !== 'string' || typeof fundName !== 'string') {
      return results;
    }

    if (fundCode.toLocaleLowerCase().includes(normalizedKeyword)) {
      results.push({ fundName, fundCode });
    }
    return results;
  }, []);
};
