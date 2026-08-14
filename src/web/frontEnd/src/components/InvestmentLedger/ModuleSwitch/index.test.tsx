import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ModuleSwitch from './index';

describe('ModuleSwitch', () => {
  it('以受控 Radio.Group 展示持仓与历史交易记录两个独立模块', () => {
    const { container } = render(
      <ModuleSwitch activeModule="holdings" onSwitch={() => undefined} />,
    );

    expect(screen.getByRole('navigation', { name: '账本模块导航' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '持仓' })).toBeChecked();
    expect(screen.getByRole('radio', { name: '历史交易记录' })).not.toBeChecked();
    expect(screen.getAllByRole('radio')).toHaveLength(2);
    expect(container.querySelector('[style]')).toBeNull();
  });

  it('切换时只回调容器且不改变 URL', () => {
    const onSwitch = vi.fn();
    const initialUrl = window.location.href;
    render(<ModuleSwitch activeModule="holdings" onSwitch={onSwitch} />);

    fireEvent.click(screen.getByRole('radio', { name: '历史交易记录' }));

    expect(onSwitch).toHaveBeenCalledOnce();
    expect(onSwitch).toHaveBeenCalledWith('history');
    expect(window.location.href).toBe(initialUrl);
  });

  it('由容器更新 activeModule 后同步受控选中项', () => {
    const { rerender } = render(
      <ModuleSwitch activeModule="history" onSwitch={() => undefined} />,
    );

    expect(screen.getByRole('radio', { name: '历史交易记录' })).toBeChecked();
    rerender(<ModuleSwitch activeModule="holdings" onSwitch={() => undefined} />);
    expect(screen.getByRole('radio', { name: '持仓' })).toBeChecked();
  });
});
