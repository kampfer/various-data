import React from 'react';
import { Button, InputNumber, Pagination, Select, message } from 'antd';
import QueryInputValidator from '../../../domain/ledger/QueryInputValidator';
import { MAX_PAGE_SIZE, MIN_PAGE_SIZE, PAGE_SIZE_OPTIONS } from '../../../domain/ledger/constants';
import styles from './index.module.scss';

/** 分页器输入契约（需求 2.24-2.31）。 */
export interface LedgerPaginationProps {
  readonly page: number;
  readonly pageSize: number;
  readonly pageCount: number;
  readonly total: number;
  readonly onPageChange: (page: number) => void;
  readonly onPageSizeChange: (size: number) => void;
}

/** 分页器内部仅保存尚未应用的自定义页大小草稿。 */
interface LedgerPaginationState {
  readonly customPageSize: number | null;
}

/** 组合 antd 分页器、预设页大小与经领域校验器验证的自定义输入。 */
export default class LedgerPagination extends React.Component<LedgerPaginationProps, LedgerPaginationState> {
  public override state: LedgerPaginationState = { customPageSize: null };

  private readonly validator = new QueryInputValidator();

  /** 应用页大小前统一走领域校验，失败时不触发外部状态变更。 */
  private readonly applyPageSize = (size: unknown): void => {
    const result = this.validator.validatePageSize(size);
    if (!result.valid) {
      void message.error(result.fieldErrors[0]?.message ?? '自定义页大小无效');
      return;
    }
    this.props.onPageSizeChange(size as number);
    this.setState({ customPageSize: null });
  };

  /** 处理 antd Pagination 的翻页及内置预设页大小切换。 */
  private readonly handlePaginationChange = (page: number, pageSize: number): void => {
    if (pageSize !== this.props.pageSize) {
      this.applyPageSize(pageSize);
      return;
    }
    const result = this.validator.validatePage(page, this.props.pageCount);
    if (!result.valid) {
      void message.error(result.fieldErrors[0]?.message ?? '请求的页码无效');
      return;
    }
    this.props.onPageChange(page);
  };

  /** 更新自定义页大小草稿，不提前改变已应用页大小。 */
  private readonly handleCustomPageSizeChange = (value: number | null): void => {
    this.setState({ customPageSize: value });
  };

  /** 提交自定义页大小。 */
  private readonly handleCustomPageSizeSubmit = (): void => {
    this.applyPageSize(this.state.customPageSize);
  };

  /** 空结果仍提供预设页大小选择，但不渲染任何有效页码。 */
  private readonly renderEmptyPageSizeSelector = (): React.ReactNode => (
    <Select
      aria-label="预设页大小"
      className={styles.presetSelector}
      value={PAGE_SIZE_OPTIONS.includes(this.props.pageSize as 10 | 20 | 50) ? this.props.pageSize : undefined}
      placeholder="选择页大小"
      options={PAGE_SIZE_OPTIONS.map((size) => ({ value: size, label: `每页 ${size} 条` }))}
      onChange={this.applyPageSize}
    />
  );

  /** 当前页与总页数文案。 */
  private readonly renderPageSummary = (): string =>
    `第 ${this.props.page} 页 / 共 ${this.props.pageCount} 页`;

  public override render(): React.ReactNode {
    const { page, pageSize, pageCount, total } = this.props;
    return (
      <section className={styles.container} aria-label="账本分页">
        <div className={styles.navigation}>
          {pageCount === 0 ? (
            <>
              <span className={styles.emptyMessage}>当前结果没有可浏览的页</span>
              {this.renderEmptyPageSizeSelector()}
            </>
          ) : (
            <Pagination
              current={page}
              pageSize={pageSize}
              total={total}
              showSizeChanger
              pageSizeOptions={PAGE_SIZE_OPTIONS.map(String)}
              showTotal={this.renderPageSummary}
              onChange={this.handlePaginationChange}
            />
          )}
        </div>
        <div className={styles.customSize}>
          <InputNumber<number>
            aria-label="自定义页大小"
            value={this.state.customPageSize}
            placeholder={`${MIN_PAGE_SIZE}-${MAX_PAGE_SIZE}`}
            onChange={this.handleCustomPageSizeChange}
          />
          <Button onClick={this.handleCustomPageSizeSubmit}>应用自定义页大小</Button>
        </div>
      </section>
    );
  }
}
