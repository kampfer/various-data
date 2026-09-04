import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ModuleSwitch from './index';

describe('ModuleSwitch', () => {
  it('以受控 Menu 展示三个独立模块', () => {
    render(
      <ModuleSwitch selectedModule="holdings" onSwitch={() => undefined} />,
    );

    expect(screen.getByRole('navigation', { name: '账本模块导航' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: '持仓' })).toHaveClass('ant-menu-item-selected');
    expect(screen.getByRole('menuitem', { name: '历史交易记录' })).not.toHaveClass('ant-menu-item-selected');
    expect(screen.getAllByRole('menuitem')).toHaveLength(3);
  });

  it('账户管理可作为第三个独立导航模块使用', () => {
    const onSwitch = vi.fn();
    render(<ModuleSwitch selectedModule="accounts" onSwitch={onSwitch} />);

    expect(screen.getByRole('menuitem', { name: '账户管理' })).toHaveClass('ant-menu-item-selected');
    fireEvent.click(screen.getByRole('menuitem', { name: '账户管理' }));
    expect(onSwitch).toHaveBeenCalledWith('accounts');
  });

  it('切换时只回调父布局，由父布局负责 URL 导航', () => {
    const onSwitch = vi.fn();
    render(<ModuleSwitch selectedModule="holdings" onSwitch={onSwitch} />);

    fireEvent.click(screen.getByRole('menuitem', { name: '历史交易记录' }));

    expect(onSwitch).toHaveBeenCalledOnce();
    expect(onSwitch).toHaveBeenCalledWith('history');
  });

  it('由 URL 派生的 selectedModule 更新后同步受控选中项', () => {
    const { rerender } = render(
      <ModuleSwitch selectedModule="history" onSwitch={() => undefined} />,
    );

    expect(screen.getByRole('menuitem', { name: '历史交易记录' })).toHaveClass('ant-menu-item-selected');
    rerender(<ModuleSwitch selectedModule="holdings" onSwitch={() => undefined} />);
    expect(screen.getByRole('menuitem', { name: '持仓' })).toHaveClass('ant-menu-item-selected');
  });
});
