import React from 'react';
import { Menu } from 'antd';
import type { MenuProps } from 'antd';
import type { LedgerModule } from '../../../domain/ledger/constants';
import styles from './index.module.scss';

/** 模块导航属性：选中项由当前 URL 派生，切换回调由父布局负责路由导航。 */
export interface ModuleSwitchProps {
  /** 当前 URL 对应的选中模块码，不读取 Redux 模块状态。 */
  readonly selectedModule: LedgerModule;
  /** 模块切换回调；不会修改 Redux 查询快照。 */
  readonly onSwitch: (module: LedgerModule) => void;
}

/** 两个账本子路由的无状态导航菜单。 */
export default class ModuleSwitch extends React.Component<ModuleSwitchProps> {
  private readonly handleClick: MenuProps['onClick'] = ({ key }): void => {
    if (key === 'holdings' || key === 'history') this.props.onSwitch(key);
  };

  public override render(): React.ReactNode {
    return (
      <nav className={styles.container} aria-label="账本模块导航">
        <Menu
          mode="inline"
          selectedKeys={[this.props.selectedModule]}
          items={[
            { key: 'holdings', label: '持仓' },
            { key: 'history', label: '历史交易记录' },
          ]}
          onClick={this.handleClick}
        />
      </nav>
    );
  }
}
