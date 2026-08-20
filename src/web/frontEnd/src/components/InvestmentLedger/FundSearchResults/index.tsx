import React from 'react';
import { Empty, Spin } from 'antd';
import type { FundSearchOut } from '../../../api/types';
import styles from './index.module.scss';

/**
 * 基金搜索结果列表（受控展示组件，本次新增，需求 5.4）。
 *
 * 约束（与设计文档「前端设计 7/8」一致）：
 *   1. 无自身请求、无 Redux 依赖；结果与加载态全部由 props 注入。
 *   2. 仅展示「基金名称 + 基金代码」逐条结果与空态提示；选中结果回调交由容器处理。
 *   3. 不出现 `style={{...}}`；样式全部经 CSS Modules。
 *   4. 列表项使用 `button` 语义以保证可访问性与键盘可达，并通过 `aria-label` 拼接名称与代码。
 */
export interface FundSearchResultsProps {
  /** 是否加载中；true 时渲染加载提示 */
  readonly loading: boolean;
  /** 当前结果集；空数组配合 loading=false 渲染空态提示 */
  readonly results: readonly FundSearchOut[];
  /** 选中某条结果；参数为该条目的名称与代码（需求 5.5） */
  readonly onSelect: (fundName: string, fundCode: string) => void;
}

/**
 * 基金搜索结果列表。
 *
 * 渲染分支：
 * - 加载中：渲染 Spin 加载提示；
 * - 无加载且无结果：渲染 Empty 空态提示，保留输入；
 * - 无加载且有结果：逐条渲染「基金名称 + 基金代码」，点击触发 onSelect。
 */
export default class FundSearchResults extends React.Component<FundSearchResultsProps> {
  /** 选中某条结果：调用 onSelect 回调，把名称与代码交给容器回填草稿。 */
  private readonly handleSelect = (item: FundSearchOut): void => {
    this.props.onSelect(item.fundName, item.fundCode);
  };

  public override render(): React.ReactNode {
    const { loading, results } = this.props;

    // 仅在加载中时渲染加载提示，避免空结果时误显示加载态
    if (loading) {
      return (
        <div className={`${styles.results} ${styles.status}`} role="status" aria-live="polite">
          <Spin size="small" />
          <span className={styles.hint}>正在搜索基金…</span>
        </div>
      );
    }

    // 无加载且无结果：渲染空态提示，保留输入（需求 5.4）
    if (results.length === 0) {
      return (
        <div className={`${styles.results} ${styles.emptyWrap}`}>
          <Empty
            className={styles.empty}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="没有匹配的基金"
          />
        </div>
      );
    }

    return (
      <ul className={styles.results} role="listbox" aria-label="基金搜索结果">
        {results.map((item) => (
          <li key={`${item.fundCode}-${item.fundName}`} className={styles.item}>
            <button
              type="button"
              className={styles.option}
              aria-label={`选择基金 ${item.fundName} ${item.fundCode}`}
              onClick={() => this.handleSelect(item)}
            >
              <span className={styles.name}>{item.fundName}</span>
              <span className={styles.code}>{item.fundCode}</span>
            </button>
          </li>
        ))}
      </ul>
    );
  }
}
