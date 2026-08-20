// FundSearchResults 的渲染分支定向测试（任务 16.4）。
//
// 测试目标：覆盖三条渲染分支与选中交互
//   1. 加载中：渲染 Spin + 中文加载提示，不渲染空态/列表（需求 5.3、5.4）；
//   2. 无结果：渲染 Empty 空态，保留输入；
//   3. 有结果：逐条渲染「基金名称 + 基金代码」，点击触发 onSelect 回调（需求 5.5）。
// Validates: Requirements 5.4, 5.5
import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import FundSearchResults from './index';
import type { FundSearchOut } from '../../../api/types';

describe('FundSearchResults', () => {
  it('加载中时渲染加载提示且不渲染空态与列表项', () => {
    render(<FundSearchResults loading={true} results={[]} onSelect={() => undefined} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('正在搜索基金…')).toBeInTheDocument();
    // 列表/空态不应出现
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(screen.queryByText('没有匹配的基金')).not.toBeInTheDocument();
  });

  it('无加载且无结果时渲染空态提示，不渲染列表', () => {
    render(<FundSearchResults loading={false} results={[]} onSelect={() => undefined} />);

    expect(screen.getByText('没有匹配的基金')).toBeInTheDocument();
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    // 加载提示也不应出现
    expect(screen.queryByText('正在搜索基金…')).not.toBeInTheDocument();
  });

  it('有结果时逐条渲染基金名称与代码，点击触发 onSelect 并携带名称与代码', () => {
    const onSelect = vi.fn();
    const results: FundSearchOut[] = [
      { fundName: '易方达蓝筹精选混合', fundCode: '005827' },
      { fundName: '华夏沪深300ETF联接A', fundCode: '000051' },
    ];
    render(<FundSearchResults loading={false} results={results} onSelect={onSelect} />);

    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();

    // 逐条渲染名称与代码
    expect(screen.getByText('易方达蓝筹精选混合')).toBeInTheDocument();
    expect(screen.getByText('005827')).toBeInTheDocument();
    expect(screen.getByText('华夏沪深300ETF联接A')).toBeInTheDocument();
    expect(screen.getByText('000051')).toBeInTheDocument();

    // 点击第一项：触发 onSelect 并携带名称与代码
    fireEvent.click(screen.getByLabelText('选择基金 易方达蓝筹精选混合 005827'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('易方达蓝筹精选混合', '005827');
  });
});
