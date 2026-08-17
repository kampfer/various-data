import React from 'react';
import { DatePicker, Input, Select, Tag, message } from 'antd';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ChangeEvent } from 'react';
import type { LedgerModule, ProductType, TradeDirection } from '../../../domain/ledger/constants';
import type { LedgerQuerySnapshot } from '../../../domain/ledger/LedgerQueryState';
import QueryInputValidator from '../../../domain/ledger/QueryInputValidator';
import { productTypeOptions, tradeDirectionOptions } from '../../../domain/ledger/labels';
import styles from './index.module.scss';

const { RangePicker } = DatePicker;

type DateRangeValue = [Dayjs | null, Dayjs | null] | null;

/** 把已应用的 YYYY-MM-DD 日期转换为 antd RangePicker 使用的 Dayjs。 */
const toDateRange = (start: string | null, end: string | null): DateRangeValue => {
  if (start === null && end === null) return null;
  return [start === null ? null : dayjs(start), end === null ? null : dayjs(end)];
};

/** 筛选与搜索栏输入契约（需求 2.16-2.21）。 */
export interface TradeFilterBarProps {
  /** 当前已应用查询；成功回调前不会被组件修改。 */
  readonly query: LedgerQuerySnapshot;
  /** 当前所在模块。 */
  readonly module: LedgerModule;
  /** 仅在待应用输入校验通过后调用。 */
  readonly onApply: (patch: Partial<LedgerQuerySnapshot>) => void;
  /** 清除产品历史交易范围。 */
  readonly onClearScope: () => void;
}

/** 组件内保存尚未应用的搜索值和日期范围草稿。 */
interface TradeFilterBarState {
  readonly productName: string;
  readonly productCode: string;
  readonly dateRange: DateRangeValue;
}

/** 交易筛选与搜索展示组件；只通过 props 回调向容器提交查询补丁。 */
export default class TradeFilterBar extends React.Component<TradeFilterBarProps, TradeFilterBarState> {
  public override state: TradeFilterBarState = {
    productName: this.props.query.productName ?? '',
    productCode: this.props.query.productCode ?? '',
    dateRange: toDateRange(this.props.query.startDate, this.props.query.endDate),
  };

  private readonly validator = new QueryInputValidator();

  /** 外部重置或切换模块后，用新的已应用查询同步本地草稿。 */
  public override componentDidUpdate(previousProps: TradeFilterBarProps): void {
    const query = this.props.query;
    const previousQuery = previousProps.query;
    const searchChanged = previousQuery.productName !== query.productName
      || previousQuery.productCode !== query.productCode;
    const dateChanged = previousQuery.startDate !== query.startDate
      || previousQuery.endDate !== query.endDate;

    if (searchChanged || dateChanged) {
      this.setState({
        productName: searchChanged ? query.productName ?? '' : this.state.productName,
        productCode: searchChanged ? query.productCode ?? '' : this.state.productCode,
        dateRange: dateChanged
          ? toDateRange(query.startDate, query.endDate)
          : this.state.dateRange,
      });
    }
  }

  /** 显示校验器提供的首条中文错误，不向容器提交查询。 */
  private readonly showValidationError = (fallback: string, result: ReturnType<QueryInputValidator['validateSearchValue']>): void => {
    void message.error(result.fieldErrors[0]?.message ?? fallback);
  };

  /** 产品类型筛选使用稳定英文码，清除时提交 null。 */
  private readonly handleProductTypeChange = (value: ProductType | undefined): void => {
    this.props.onApply({ productType: value ?? null });
  };

  /** 交易方向筛选使用稳定英文码，清除时提交 null。 */
  private readonly handleDirectionChange = (value: TradeDirection | undefined): void => {
    this.props.onApply({ direction: value ?? null });
  };

  /** 日历展开期间只同步草稿，完整选择或清空后自动校验并应用。 */
  private readonly handleDateCalendarChange = (dates: DateRangeValue): void => {
    this.setState({ dateRange: dates });
  };

  private readonly handleDateRangeChange = (dates: DateRangeValue): void => {
    this.setState({ dateRange: dates });
    this.applyDateRange(dates);
  };

  /** 日期范围两端同时为空代表清除筛选；其它情况必须完整且有效。 */
  private readonly applyDateRange = (dateRange: DateRangeValue): void => {
    const startDate = dateRange?.[0]?.format('YYYY-MM-DD') ?? null;
    const endDate = dateRange?.[1]?.format('YYYY-MM-DD') ?? null;
    const result = this.validator.validateDateRange(startDate, endDate);
    if (!result.valid) {
      this.showValidationError('交易日期范围无效', result);
      return;
    }
    this.props.onApply({ startDate, endDate });
  };

  /** 搜索输入保留草稿；清空已应用条件时立即同步查询。 */
  private readonly handleProductNameChange = (event: ChangeEvent<HTMLInputElement>): void => {
    const productName = event.target.value;
    this.setState({ productName });
    if (productName === '' && this.props.query.productName !== null) {
      this.props.onApply({ productName: null });
    }
  };

  private readonly handleProductCodeChange = (event: ChangeEvent<HTMLInputElement>): void => {
    const productCode = event.target.value;
    this.setState({ productCode });
    if (productCode === '' && this.props.query.productCode !== null) {
      this.props.onApply({ productCode: null });
    }
  };

  /** 产品名称和产品代码分别校验、分别应用，可与另一搜索条件共同生效。 */
  private readonly applySearch = (field: 'productName' | 'productCode', value: string): void => {
    const result = this.validator.validateSearchValue(value);
    if (!result.valid) {
      this.showValidationError('搜索值无效', result);
      return;
    }
    this.props.onApply({ [field]: value });
  };

  public override render(): React.ReactNode {
    const { query, module } = this.props;
    const scoped = module === 'history'
      && query.scopeProductType !== null
      && query.scopeProductCode !== null;

    return (
      <section className={styles.container} aria-label="交易筛选与搜索">
        {scoped && (
          <Tag
            className={styles.scope}
            color="blue"
            closable
            closeIcon={<span aria-label="清除范围">×</span>}
            onClose={this.props.onClearScope}
          >
            产品范围：{query.scopeProductCode}
          </Tag>
        )}
        <Select<ProductType>
          aria-label="产品类型筛选"
          className={styles.select}
          allowClear
          virtual={false}
          placeholder="产品类型"
          value={query.productType ?? undefined}
          options={[...productTypeOptions()]}
          onChange={this.handleProductTypeChange}
        />
        <Select<TradeDirection>
          aria-label="交易方向筛选"
          className={styles.select}
          allowClear
          virtual={false}
          placeholder="交易方向"
          value={query.direction ?? undefined}
          options={[...tradeDirectionOptions()]}
          onChange={this.handleDirectionChange}
        />
        <RangePicker
          aria-label="交易日期范围"
          className={styles.datePicker}
          value={this.state.dateRange}
          format="YYYY-MM-DD"
          onCalendarChange={this.handleDateCalendarChange}
          onChange={this.handleDateRangeChange}
        />
        <Input
          aria-label="产品名称搜索"
          className={styles.searchInput}
          allowClear
          value={this.state.productName}
          placeholder="产品名称（回车搜索）"
          onChange={this.handleProductNameChange}
          onPressEnter={(event) => this.applySearch('productName', event.currentTarget.value)}
        />
        <Input
          aria-label="产品代码搜索"
          className={styles.searchInput}
          allowClear
          value={this.state.productCode}
          placeholder="产品代码（回车搜索）"
          onChange={this.handleProductCodeChange}
          onPressEnter={(event) => this.applySearch('productCode', event.currentTarget.value)}
        />
      </section>
    );
  }
}
