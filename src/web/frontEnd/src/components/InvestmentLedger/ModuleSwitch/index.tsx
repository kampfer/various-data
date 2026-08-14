import React from 'react';
import { Radio } from 'antd';
import type { RadioChangeEvent } from 'antd';
import type { LedgerModule } from '../../../domain/ledger/constants';
import styles from './index.module.scss';

/** 模块切换器属性：受控值由容器提供，切换事件只通知容器（需求 2.1、2.13）。 */
export interface ModuleSwitchProps {
  /** 当前激活模块码，决定选中的单选项。 */
  readonly activeModule: LedgerModule;
  /** 模块切换回调；目标模块的浏览状态重置由容器与状态层负责。 */
  readonly onSwitch: (module: LedgerModule) => void;
}

/** 两个账本模块的受控切换入口，不持有状态，也不操作浏览器 URL。 */
export default class ModuleSwitch extends React.Component<ModuleSwitchProps> {
  /** 将 antd 变更事件转换为领域模块码并上交容器。 */
  private readonly handleChange = (event: RadioChangeEvent): void => {
    const module = event.target.value as LedgerModule;
    this.props.onSwitch(module);
  };

  public override render(): React.ReactNode {
    return (
      <nav className={styles.container} aria-label="账本模块导航">
        <Radio.Group
          aria-label="账本模块切换"
          buttonStyle="solid"
          optionType="button"
          value={this.props.activeModule}
          onChange={this.handleChange}
          options={[
            { label: '持仓', value: 'holdings' },
            { label: '历史交易记录', value: 'history' },
          ]}
        />
      </nav>
    );
  }
}
