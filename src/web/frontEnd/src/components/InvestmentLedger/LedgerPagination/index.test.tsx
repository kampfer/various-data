import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import LedgerPagination from './index';

describe('LedgerPagination', () => {
  it('显示当前页与总页数，并允许翻到有效页', () => {
    const requestedPages: number[] = [];
    render(
      <LedgerPagination
        page={2}
        pageSize={10}
        pageCount={3}
        total={25}
        onPageChange={(page) => requestedPages.push(page)}
        onPageSizeChange={() => undefined}
      />,
    );

    expect(screen.getByText('第 2 页 / 共 3 页')).toBeInTheDocument();
    fireEvent.click(screen.getByTitle('3'));
    expect(requestedPages).toEqual([3]);
  });

  it('空结果不标记有效页，并仍提供 10/20/50 三个预设页大小', async () => {
    const appliedSizes: number[] = [];
    render(
      <LedgerPagination
        page={1}
        pageSize={20}
        pageCount={0}
        total={0}
        onPageChange={() => undefined}
        onPageSizeChange={(size) => appliedSizes.push(size)}
      />,
    );

    expect(screen.getByText('当前结果没有可浏览的页')).toBeInTheDocument();
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '预设页大小' }));
    const listbox = await screen.findByRole('listbox');
    expect(within(listbox).getByRole('option', { name: '每页 10 条' })).toBeInTheDocument();
    expect(within(listbox).getByRole('option', { name: '每页 20 条' })).toBeInTheDocument();
    expect(within(listbox).getByRole('option', { name: '每页 50 条' })).toBeInTheDocument();
    fireEvent.click(screen.getByText('每页 50 条'));
    expect(appliedSizes).toEqual([50]);
  });

  it('只应用 1 至 100 的整数自定义页大小', async () => {
    const appliedSizes: number[] = [];
    render(
      <LedgerPagination
        page={1}
        pageSize={20}
        pageCount={2}
        total={30}
        onPageChange={() => undefined}
        onPageSizeChange={(size) => appliedSizes.push(size)}
      />,
    );

    const input = screen.getByLabelText('自定义页大小');
    fireEvent.change(input, { target: { value: '101' } });
    fireEvent.click(screen.getByRole('button', { name: '应用自定义页大小' }));
    expect(appliedSizes).toEqual([]);
    await waitFor(() => {
      expect(screen.getByText('自定义页大小必须为 1 至 100 的整数')).toBeInTheDocument();
    });

    fireEvent.change(input, { target: { value: '25' } });
    fireEvent.click(screen.getByRole('button', { name: '应用自定义页大小' }));
    expect(appliedSizes).toEqual([25]);
  });
});
