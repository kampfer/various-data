import React from 'react';
import { Button, DatePicker, Input, Select, Tag, message } from 'antd';
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

  /** RangePicker 的选择只更新草稿，点击应用后才校验并提交。 */
  private readonly handleDateRangeChange = (dates: DateRangeValue): void => {
    this.setState({ dateRange: dates });
  };

  /** 日期范围两端同时为空代表清除筛选；其它情况必须完整且有效。 */
  private readonly applyDateRange = (): void => {
    const startDate = this.state.dateRange?.[0]?.format('YYYY-MM-DD') ?? null;
    const endDate = this.state.dateRange?.[1]?.format('YYYY-MM-DD') ?? null;
    const result = this.validator.validateDateRange(startDate, endDate);
    if (!result.valid) {
      this.showValidationError('交易日期范围无效', result);
      return;
    }
    this.props.onApply({ startDate, endDate });
  };
  /** 搜索输入只更新本地草稿，避免无效值提前改变已应用结果。 */
  private readonly handleProductNameChange = (event: ChangeEvent<HTMLInputElement>): void => {
    this.setState({ productName: event.target.value });
  };

  private readonly handleProductCodeChange = (event: ChangeEvent<HTMLInputElement>): void => {
    this.setState({ productCode: event.target.value });
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

  private readonly clearSearch = (field: 'productName' | 'productCode'): void => {
    if (field === 'productName') {
      this.setState({ productName: '' });
    } else {
      this.setState({ productCode: '' });
    }
    this.props.onApply({ [field]: null });
  };

  public override render(): React.ReactNode {
    const { query, module } = this.props;
    const scoped = module === 'history'
      && query.scopeProductType !== null
      && query.scopeProductCode !== null;

    return (
      <section className={styles.container} aria-label="交易筛选与搜索">
        {scoped && (
          <div className={styles.scope} aria-label="产品历史交易范围">
            <Tag color="blue">产品范围：{query.scopeProductCode}</Tag>
            <Button type="link" onClick={this.props.onClearScope}>清除范围</Button>
          </div>
        )}
        <div className={styles.filters}>
          <Select<ProductType>
            aria-label="产品类型筛选"
            className={styles.select}
            allowClear
            virtual={false}
            placeholder="全部产品类型"
            value={query.productType ?? undefined}
            options={[...productTypeOptions()]}
            onChange={this.handleProductTypeChange}
          />
          <Select<TradeDirection>
            aria-label="交易方向筛选"
            className={styles.select}
            allowClear
            virtual={false}
            placeholder="全部交易方向"
            value={query.direction ?? undefined}
            options={[...tradeDirectionOptions()]}
            onChange={this.handleDirectionChange}
          />
          <div className={styles.dateFilter}>
            <RangePicker
              aria-label="交易日期范围"
              value={this.state.dateRange}
              format="YYYY-MM-DD"
              onCalendarChange={this.handleDateRangeChange}
              onChange={this.handleDateRangeChange}
            />
            <Button onClick={this.applyDateRange}>应用日期范围</Button>
          </div>
        </div>
        <div className={styles.searches}>
          <div className={styles.searchItem}>
            <Input.Search
              aria-label="产品名称搜索"
              allowClear
              value={this.state.productName}
              placeholder="输入产品名称"
              enterButton="搜索产品名称"
              onChange={this.handleProductNameChange}
              onSearch={(value) => this.applySearch('productName', value)}
            />
            <Button onClick={() => this.clearSearch('productName')}>清除产品名称</Button>
          </div>
          <div className={styles.searchItem}>
            <Input.Search
              aria-label="产品代码搜索"
              allowClear
              value={this.state.productCode}
              placeholder="输入产品代码"
              enterButton="搜索产品代码"
              onChange={this.handleProductCodeChange}
              onSearch={(value) => this.applySearch('productCode', value)}
            />
            <Button onClick={() => this.clearSearch('productCode')}>清除产品代码</Button>
          </div>
        </div>
      </section>
    );
  }
}
