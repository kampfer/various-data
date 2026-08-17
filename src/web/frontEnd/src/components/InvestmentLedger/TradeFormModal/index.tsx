import React from 'react';
import { DatePicker, Form, Input, Modal, Select } from 'antd';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ChangeEvent } from 'react';
import type { FieldErrorItem, TradeDraft } from '../../../api/types';
import type { ProductType, TradeDirection } from '../../../domain/ledger/constants';
import TradeDraftValidator from '../../../domain/ledger/TradeDraftValidator';
import { productTypeOptions, tradeDirectionOptions, TRADE_VALUE_LABELS } from '../../../domain/ledger/labels';
import styles from './index.module.scss';

/** 交易日期展示与提交格式；与后端及校验器保持一致的 YYYY-MM-DD。 */
const TRADE_DATE_FORMAT = 'YYYY-MM-DD';

/** 把 YYYY-MM-DD 字符串转换为 DatePicker 所需的 Dayjs；空或非法时返回 null。 */
const toTradeDateDayjs = (value: string | null | undefined): Dayjs | null => {
  if (typeof value !== 'string' || value.length === 0) return null;
  const day = dayjs(value, TRADE_DATE_FORMAT, true);
  return day.isValid() ? day : null;
};

export interface TradeFormModalProps { readonly visible: boolean; readonly draft: TradeDraft; readonly fieldErrors: readonly FieldErrorItem[]; readonly submitting: boolean; readonly onChange: (patch: Partial<TradeDraft>) => void; readonly onSubmit: (draft: TradeDraft) => void; readonly onCancel: () => void; }
interface TradeFormModalState { readonly fieldErrors: readonly FieldErrorItem[]; }
/** 新建交易表单：字段状态使用 canonical 名称，标签仅随产品类型渲染。 */
export default class TradeFormModal extends React.Component<TradeFormModalProps, TradeFormModalState> {
  public override state: TradeFormModalState = { fieldErrors: this.props.fieldErrors };
  private readonly validator = new TradeDraftValidator();
  public override componentDidUpdate(previousProps: TradeFormModalProps): void { if (previousProps.fieldErrors !== this.props.fieldErrors || (!previousProps.visible && this.props.visible)) this.setState({ fieldErrors: this.props.fieldErrors }); }
  private readonly changeField = <K extends keyof TradeDraft,>(field: K, value: TradeDraft[K]): void => { this.setState((current) => ({ fieldErrors: current.fieldErrors.filter((error) => error.field !== field) })); this.props.onChange({ [field]: value } as Partial<TradeDraft>); };
  private readonly changeText = (field: keyof TradeDraft) => (event: ChangeEvent<HTMLInputElement>): void => this.changeField(field, event.target.value);
  /** DatePicker 选择后把 Dayjs 规范化为 YYYY-MM-DD 文本，保持草稿仍为可序列化字符串。 */
  private readonly changeTradeDate = (value: Dayjs | null): void => this.changeField('tradeDate', value === null ? null : value.format(TRADE_DATE_FORMAT));
  private errorFor(field: keyof TradeDraft): string | undefined { return this.state.fieldErrors.find((error) => error.field === field)?.message; }
  private readonly submit = (): void => { const result = this.validator.validate(this.props.draft); this.setState({ fieldErrors: result.fieldErrors }); if (result.valid) this.props.onSubmit(this.props.draft); };
  public override render(): React.ReactNode {
    const { visible, draft, submitting, onCancel } = this.props;
    const type = draft.productType ?? 'FUND'; const labels = TRADE_VALUE_LABELS[type];
    return <Modal open={visible} title="新建交易记录" okText="创建交易" cancelText="取消" confirmLoading={submitting} onOk={this.submit} onCancel={onCancel}>
      <Form className={styles.form} layout="vertical" autoComplete="off"><div className={styles.grid}>
        <Form.Item label="产品类型" required validateStatus={this.errorFor('productType') ? 'error' : undefined} help={this.errorFor('productType')}><Select<ProductType> aria-label="产品类型" className={styles.fullWidth} virtual={false} placeholder="请选择产品类型" value={draft.productType ?? undefined} options={[...productTypeOptions()]} onChange={(value) => this.changeField('productType', value)} /></Form.Item>
        <Form.Item label="交易方向" required validateStatus={this.errorFor('direction') ? 'error' : undefined} help={this.errorFor('direction')}><Select<TradeDirection> aria-label="交易方向" className={styles.fullWidth} virtual={false} placeholder="请选择交易方向" value={draft.direction ?? undefined} options={[...tradeDirectionOptions()]} onChange={(value) => this.changeField('direction', value)} /></Form.Item>
        <Form.Item label="产品名称" required validateStatus={this.errorFor('productName') ? 'error' : undefined} help={this.errorFor('productName')}><Input aria-label="产品名称" value={draft.productName ?? ''} onChange={this.changeText('productName')} /></Form.Item>
        <Form.Item label="产品代码" required validateStatus={this.errorFor('productCode') ? 'error' : undefined} help={this.errorFor('productCode')}><Input aria-label="产品代码" value={draft.productCode ?? ''} onChange={this.changeText('productCode')} /></Form.Item>
        <Form.Item label={labels.price} required validateStatus={this.errorFor('transactionPrice') ? 'error' : undefined} help={this.errorFor('transactionPrice')}><Input aria-label={labels.price} inputMode="decimal" value={draft.transactionPrice ?? ''} onChange={this.changeText('transactionPrice')} /></Form.Item>
        <Form.Item label={labels.quantity} required validateStatus={this.errorFor('transactionQuantity') ? 'error' : undefined} help={this.errorFor('transactionQuantity')}><Input aria-label={labels.quantity} inputMode="decimal" value={draft.transactionQuantity ?? ''} onChange={this.changeText('transactionQuantity')} /></Form.Item>
        <Form.Item label="交易日期" required validateStatus={this.errorFor('tradeDate') ? 'error' : undefined} help={this.errorFor('tradeDate')}><DatePicker aria-label="交易日期" className={styles.fullWidth} format={TRADE_DATE_FORMAT} value={toTradeDateDayjs(draft.tradeDate)} onChange={this.changeTradeDate} /></Form.Item>
      </div></Form></Modal>;
  }
}
