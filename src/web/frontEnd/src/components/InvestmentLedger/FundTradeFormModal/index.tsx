import React from 'react';
import { DatePicker, Form, Input, Modal, Select } from 'antd';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ChangeEvent } from 'react';
import type {
  AccountOut,
  FieldErrorItem,
  FundSearchOut,
  TradeDraft,
} from '../../../api/types';
import type { TradeDirection } from '../../../domain/ledger/constants';
import FundSearchController from '../../../domain/ledger/FundSearchController';
import TradeDraftValidator from '../../../domain/ledger/TradeDraftValidator';
import computeTransactionAmount from '../../../domain/ledger/transactionAmount';
import { nextWorkingDay } from '../../../domain/ledger/businessDay';
import { formatPriceByProductType } from '../../../domain/ledger/formatNumbers';
import {
  formatAccountDisplayName,
  tradeDirectionOptions,
} from '../../../domain/ledger/labels';
import FundSearchResults from '../FundSearchResults';
import styles from './index.module.scss';

/** 交易日期和确认日期统一使用后端约定的 YYYY-MM-DD 文本格式。 */
const TRADE_DATE_FORMAT = 'YYYY-MM-DD';

/** 把草稿中的日期文本转换为 DatePicker 所需的 Dayjs。 */
const toDateDayjs = (value: string | null | undefined): Dayjs | null => {
  if (typeof value !== 'string' || value.length === 0) return null;
  const day = dayjs(value, TRADE_DATE_FORMAT, true);
  return day.isValid() ? day : null;
};

export interface FundTradeFormModalProps {
  readonly visible: boolean;
  readonly draft: TradeDraft;
  readonly accounts: readonly AccountOut[];
  readonly fieldErrors: readonly FieldErrorItem[];
  readonly submitting: boolean;
  readonly onChange: (patch: Partial<TradeDraft>) => void;
  readonly onSubmit: (draft: TradeDraft) => void;
  readonly onCancel: () => void;
}

interface FundTradeFormModalState {
  readonly fieldErrors: readonly FieldErrorItem[];
  readonly searchResults: readonly FundSearchOut[];
  readonly searching: boolean;
  /** 输入基金代码后是否已经展示过搜索态，用于无结果空态。 */
  readonly hasSearched: boolean;
}

/**
 * 新建基金交易记录弹窗。
 *
 * 本组件独立维护表单渲染和局部搜索状态，不依赖 TradeFormModal；
 * 仅复用领域层的基金搜索、校验、金额计算和工作日工具。
 */
export default class FundTradeFormModal extends React.Component<
  FundTradeFormModalProps,
  FundTradeFormModalState
> {
  public override state: FundTradeFormModalState = {
    fieldErrors: this.props.fieldErrors,
    searchResults: [],
    searching: false,
    hasSearched: false,
  };

  /** 基金代码搜索控制器：只通过回调更新本组件局部状态。 */
  private readonly fundSearchController = new FundSearchController({
    onResults: (results) => this.setState({ searchResults: results }),
    onLoadingChange: (loading) => {
      if (loading) {
        this.setState({ searching: true, hasSearched: true });
      } else {
        this.setState({ searching: false });
      }
    },
  });

  /** 选择基金回填代码和名称时，跳过同一轮更新触发的重复搜索。 */
  private justSelected = false;

  private readonly validator = new TradeDraftValidator();

  public override componentWillUnmount(): void {
    /** 弹窗卸载时取消防抖任务，避免异步搜索回调访问已卸载组件。 */
    this.fundSearchController.dispose();
  }

  /** 清空搜索结果、空态和挂起的搜索任务。 */
  private readonly resetSearch = (): void => {
    this.setState({ hasSearched: false });
    this.fundSearchController.search('');
  };

  public override componentDidUpdate(previousProps: FundTradeFormModalProps): void {
    // Redux 返回字段错误或弹窗重新打开时，同步到组件局部错误状态。
    if (
      previousProps.fieldErrors !== this.props.fieldErrors
      || (!previousProps.visible && this.props.visible)
    ) {
      this.setState({ fieldErrors: this.props.fieldErrors });
    }

    // 关闭弹窗时清理上一次基金搜索上下文。
    if (previousProps.visible && !this.props.visible) {
      this.justSelected = false;
      this.resetSearch();
      return;
    }
    if (!this.props.visible) return;

    // 选择结果回填时，回填动作已经完成，不再重复搜索。
    if (this.justSelected) {
      this.justSelected = false;
      return;
    }

    const previousCode = previousProps.draft.productCode ?? '';
    const currentCode = this.props.draft.productCode ?? '';
    if (currentCode !== previousCode && currentCode.length > 0) {
      this.fundSearchController.search(currentCode);
    } else if (currentCode !== previousCode) {
      this.resetSearch();
    }
  }

  private readonly changeField = <K extends keyof TradeDraft>(
    field: K,
    value: TradeDraft[K],
  ): void => {
    this.setState((current) => ({
      fieldErrors: current.fieldErrors.filter((error) => error.field !== field),
    }));
    this.props.onChange({ [field]: value } as Partial<TradeDraft>);
  };

  private readonly changeText =
    (field: keyof TradeDraft) =>
      (event: ChangeEvent<HTMLInputElement>): void =>
        this.changeField(field, event.target.value);

  /** 修改基金代码时清除旧名称，防止代码和名称错配。 */
  private readonly changeFundCode = (
    event: ChangeEvent<HTMLInputElement>,
  ): void => {
    const productCode = event.target.value;
    this.setState((current) => ({
      fieldErrors: current.fieldErrors.filter(
        (error) => error.field !== 'productCode' && error.field !== 'productName',
      ),
    }));
    this.props.onChange({ productCode, productName: null });
  };

  /** 基金净值失焦时按基金展示精度格式化输入。 */
  private readonly blurPrice = (
    event: React.FocusEvent<HTMLInputElement>,
  ): void => {
    const formatted = formatPriceByProductType(event.target.value, 'FUND');
    if (formatted !== event.target.value) {
      this.changeField('transactionPrice', formatted);
    }
  };

  /** 交易日期改变时，同时填充交易日期后的下一个工作日作为确认日期。 */
  private readonly changeTradeDate = (value: Dayjs | null): void => {
    const tradeDate = value === null ? null : value.format(TRADE_DATE_FORMAT);
    const confirmationDate = value === null
      ? null
      : nextWorkingDay(value).format(TRADE_DATE_FORMAT);
    this.setState((current) => ({
      fieldErrors: current.fieldErrors.filter(
        (error) => error.field !== 'tradeDate' && error.field !== 'confirmationDate',
      ),
    }));
    this.props.onChange({ tradeDate, confirmationDate });
  };

  private errorFor(field: keyof TradeDraft): string | undefined {
    return this.state.fieldErrors.find((error) => error.field === field)?.message;
  }

  /** 选择搜索结果并回填基金名称和代码。 */
  private readonly handleSelectFund = (
    fundName: string,
    fundCode: string,
  ): void => {
    this.justSelected = true;
    this.resetSearch();
    this.props.onChange({ productName: fundName, productCode: fundCode });
  };

  /** 校验并提交固定为基金类型的草稿，保留用户编辑后的确认日期。 */
  private readonly submit = (): void => {
    const draft: TradeDraft = {
      ...this.props.draft,
      productType: 'FUND',
    };
    const result = this.validator.validate(draft);
    this.setState({ fieldErrors: result.fieldErrors });
    if (result.valid) this.props.onSubmit(draft);
  };

  public override render(): React.ReactNode {
    const { visible, draft, submitting, onCancel } = this.props;
    const activeAccounts = this.props.accounts.filter((account) => account.isActive);
    const showFundSearch =
      this.state.searching
      || this.state.searchResults.length > 0
      || this.state.hasSearched;

    return (
      <Modal
        open={visible}
        title="新建基金交易记录"
        okText="创建基金交易"
        cancelText="取消"
        confirmLoading={submitting}
        onOk={this.submit}
        onCancel={onCancel}
      >
        <Form className={styles.form} layout="vertical" autoComplete="off">
          <div className={styles.grid}>
            <Form.Item
              label="交易账户"
              required
              validateStatus={this.errorFor('accountId') ? 'error' : undefined}
              help={this.errorFor('accountId')}
            >
              <Select<number>
                aria-label="交易账户"
                className={styles.fullWidth}
                virtual={false}
                placeholder={activeAccounts.length > 0 ? '请选择交易账户' : '暂无可用账户'}
                value={draft.accountId ?? undefined}
                options={activeAccounts.map((account) => ({
                  value: account.id,
                  label: formatAccountDisplayName(account.institution, account.name) ?? account.name,
                }))}
                onChange={(value) => this.changeField('accountId', value)}
              />
            </Form.Item>
            <Form.Item
              label="交易方向"
              required
              validateStatus={this.errorFor('direction') ? 'error' : undefined}
              help={this.errorFor('direction')}
            >
              <Select<TradeDirection>
                aria-label="交易方向"
                className={styles.fullWidth}
                virtual={false}
                placeholder="请选择交易方向"
                value={draft.direction ?? undefined}
                options={[...tradeDirectionOptions()]}
                onChange={(value) => this.changeField('direction', value)}
              />
            </Form.Item>
            <Form.Item
              label="交易日期"
              required
              validateStatus={this.errorFor('tradeDate') ? 'error' : undefined}
              help={this.errorFor('tradeDate')}
            >
              <DatePicker
                aria-label="交易日期"
                className={styles.fullWidth}
                format={TRADE_DATE_FORMAT}
                value={toDateDayjs(draft.tradeDate)}
                onChange={this.changeTradeDate}
              />
            </Form.Item>
            <Form.Item
              label="确认日期"
              required
              validateStatus={this.errorFor('confirmationDate') ? 'error' : undefined}
              help={this.errorFor('confirmationDate')}
            >
              <DatePicker
                aria-label="确认日期"
                className={styles.fullWidth}
                format={TRADE_DATE_FORMAT}
                value={toDateDayjs(draft.confirmationDate)}
                onChange={(value) => this.changeField(
                  'confirmationDate',
                  value === null ? null : value.format(TRADE_DATE_FORMAT),
                )}
              />
            </Form.Item>
            <div className={styles.fundFieldsRow}>
              <Form.Item
                label="产品代码"
                required
                validateStatus={this.errorFor('productCode') ? 'error' : undefined}
                help={this.errorFor('productCode')}
              >
                <Input
                  aria-label="产品代码"
                  allowClear
                  value={draft.productCode ?? ''}
                  onChange={this.changeFundCode}
                />
              </Form.Item>
              <Form.Item
                label="产品名称"
                required
                validateStatus={this.errorFor('productName') ? 'error' : undefined}
                help={this.errorFor('productName')}
              >
                <span className={styles.readOnlyText} aria-label="产品名称">
                  {draft.productName || '选择基金后自动填入'}
                </span>
              </Form.Item>
              {showFundSearch && (
                <FundSearchResults
                  loading={this.state.searching}
                  results={this.state.searchResults}
                  onSelect={this.handleSelectFund}
                />
              )}
            </div>
            <Form.Item
              label="净值"
              required
              validateStatus={this.errorFor('transactionPrice') ? 'error' : undefined}
              help={this.errorFor('transactionPrice')}
            >
              <Input
                aria-label="净值"
                inputMode="decimal"
                allowClear
                value={draft.transactionPrice ?? ''}
                onChange={this.changeText('transactionPrice')}
                onBlur={this.blurPrice}
              />
            </Form.Item>
            <Form.Item
              label="份额"
              required
              validateStatus={this.errorFor('transactionQuantity') ? 'error' : undefined}
              help={this.errorFor('transactionQuantity')}
            >
              <Input
                aria-label="份额"
                inputMode="decimal"
                allowClear
                value={draft.transactionQuantity ?? ''}
                onChange={this.changeText('transactionQuantity')}
              />
            </Form.Item>
            <Form.Item
              label="费用"
              validateStatus={this.errorFor('fee') ? 'error' : undefined}
              help={this.errorFor('fee')}
            >
              <Input
                aria-label="费用"
                inputMode="decimal"
                allowClear
                value={draft.fee ?? ''}
                onChange={this.changeText('fee')}
              />
            </Form.Item>
          </div>
        </Form>
        <div className={styles.transactionAmount}>
          交易金额：
          <span aria-label="交易金额">
            {computeTransactionAmount(
              draft.transactionPrice,
              draft.transactionQuantity,
              draft.fee,
            )}
          </span>
        </div>
      </Modal>
    );
  }
}
