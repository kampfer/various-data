import React from 'react';
import { Form, Input, Modal, Select } from 'antd';
import type { ChangeEvent } from 'react';
import type { FieldErrorItem, TradeDraft } from '../../../api/types';
import type { ProductType, TradeDirection } from '../../../domain/ledger/constants';
import TradeDraftValidator from '../../../domain/ledger/TradeDraftValidator';
import { productTypeOptions, tradeDirectionOptions } from '../../../domain/ledger/labels';
import styles from './index.module.scss';

/** 新建交易弹窗的受控属性（需求 1.1-1.4）。 */
export interface TradeFormModalProps {
  /** 弹窗是否可见。 */
  readonly visible: boolean;
  /** 当前交易草稿；校验失败时由父级原样保留。 */
  readonly draft: TradeDraft;
  /** 领域层或服务端返回的字段级错误。 */
  readonly fieldErrors: readonly FieldErrorItem[];
  /** 是否正在提交。 */
  readonly submitting: boolean;
  /** 草稿字段变更回调。 */
  readonly onChange: (patch: Partial<TradeDraft>) => void;
  /** 有效新交易的提交回调；组件不提供编辑入口。 */
  readonly onSubmit: (draft: TradeDraft) => void;
  /** 取消并关闭弹窗。 */
  readonly onCancel: () => void;
}

/** 组件仅保存当前展示的错误，所有字段值仍由父级受控。 */
interface TradeFormModalState {
  readonly fieldErrors: readonly FieldErrorItem[];
}

/** 新建交易表单；提交前执行领域校验并逐字段展示原因。 */
export default class TradeFormModal extends React.Component<TradeFormModalProps, TradeFormModalState> {
  public override state: TradeFormModalState = { fieldErrors: this.props.fieldErrors };

  private readonly validator = new TradeDraftValidator();

  /** 同步异步提交返回的字段错误，并在重新打开时使用父级最新状态。 */
  public override componentDidUpdate(previousProps: TradeFormModalProps): void {
    if (previousProps.fieldErrors !== this.props.fieldErrors
      || (!previousProps.visible && this.props.visible)) {
      this.setState({ fieldErrors: this.props.fieldErrors });
    }
  }

  /** 更新一个受控字段并移除该字段已过期的提示。 */
  private readonly changeField = <K extends keyof TradeDraft,>(field: K, value: TradeDraft[K]): void => {
    this.setState((current) => ({
      fieldErrors: current.fieldErrors.filter((error) => error.field !== field),
    }));
    this.props.onChange({ [field]: value } as Partial<TradeDraft>);
  };

  /** 文本输入统一转发原始字符串，不格式化单价或数量。 */
  private readonly changeText = (field: keyof TradeDraft) => (event: ChangeEvent<HTMLInputElement>): void => {
    this.changeField(field, event.target.value);
  };

  /** 返回指定字段的首条中文错误，供 Form.Item 展示。 */
  private errorFor(field: keyof TradeDraft): string | undefined {
    return this.state.fieldErrors.find((error) => error.field === field)?.message;
  }

  /** 提交前校验全部字段；失败时不回调且不改变草稿。 */
  private readonly submit = (): void => {
    const result = this.validator.validate(this.props.draft);
    this.setState({ fieldErrors: result.fieldErrors });
    if (result.valid) this.props.onSubmit(this.props.draft);
  };

  public override render(): React.ReactNode {
    const { visible, draft, submitting, onCancel } = this.props;
    return (
      <Modal
        open={visible}
        title="新建交易记录"
        okText="创建交易"
        cancelText="取消"
        confirmLoading={submitting}
        onOk={this.submit}
        onCancel={onCancel}
      >
        <Form className={styles.form} layout="vertical" autoComplete="off">
          <div className={styles.grid}>
            <Form.Item label="产品类型" required validateStatus={this.errorFor('productType') ? 'error' : undefined} help={this.errorFor('productType')}>
              <Select<ProductType>
                aria-label="产品类型"
                className={styles.fullWidth}
                virtual={false}
                placeholder="请选择产品类型"
                value={draft.productType ?? undefined}
                options={[...productTypeOptions()]}
                onChange={(value) => this.changeField('productType', value)}
              />
            </Form.Item>
            <Form.Item label="交易方向" required validateStatus={this.errorFor('direction') ? 'error' : undefined} help={this.errorFor('direction')}>
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
            <Form.Item label="产品名称" required validateStatus={this.errorFor('productName') ? 'error' : undefined} help={this.errorFor('productName')}>
              <Input aria-label="产品名称" value={draft.productName ?? ''} onChange={this.changeText('productName')} />
            </Form.Item>
            <Form.Item label="产品代码" required validateStatus={this.errorFor('productCode') ? 'error' : undefined} help={this.errorFor('productCode')}>
              <Input aria-label="产品代码" value={draft.productCode ?? ''} onChange={this.changeText('productCode')} />
            </Form.Item>
            <Form.Item label="交易单价" required validateStatus={this.errorFor('unitPrice') ? 'error' : undefined} help={this.errorFor('unitPrice')}>
              <Input aria-label="交易单价" inputMode="decimal" value={draft.unitPrice ?? ''} onChange={this.changeText('unitPrice')} />
            </Form.Item>
            <Form.Item label="交易数量" required validateStatus={this.errorFor('quantity') ? 'error' : undefined} help={this.errorFor('quantity')}>
              <Input aria-label="交易数量" inputMode="numeric" value={draft.quantity ?? ''} onChange={this.changeText('quantity')} />
            </Form.Item>
            <Form.Item label="交易日期" required validateStatus={this.errorFor('tradeDate') ? 'error' : undefined} help={this.errorFor('tradeDate')}>
              <Input aria-label="交易日期" placeholder="YYYY-MM-DD" value={draft.tradeDate ?? ''} onChange={this.changeText('tradeDate')} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    );
  }
}
