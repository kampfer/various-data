import React from 'react';
import { Form, Input, Modal, Select } from 'antd';
import type { ChangeEvent } from 'react';
import type { FieldErrorItem, ValuationDraft } from '../../../api/types';
import type { ProductType } from '../../../domain/ledger/constants';
import ValuationDraftValidator from '../../../domain/ledger/ValuationDraftValidator';
import { productTypeOptions } from '../../../domain/ledger/labels';
import styles from './index.module.scss';

/** 估值维护弹窗的受控属性（需求 3.1、3.2）。 */
export interface ValuationFormModalProps {
  /** 弹窗是否可见。 */
  readonly visible: boolean;
  /** 当前估值草稿；校验失败时由父级原样保留。 */
  readonly draft: ValuationDraft;
  /** 领域层或服务端返回的字段级错误。 */
  readonly fieldErrors: readonly FieldErrorItem[];
  /** 是否正在提交。 */
  readonly submitting: boolean;
  /** 草稿字段变更回调。 */
  readonly onChange: (patch: Partial<ValuationDraft>) => void;
  /** 有效估值的提交回调。 */
  readonly onSubmit: (draft: ValuationDraft) => void;
  /** 取消并关闭弹窗。 */
  readonly onCancel: () => void;
}

/** 组件仅保存当前展示的错误，输入值始终由父级受控。 */
interface ValuationFormModalState {
  readonly fieldErrors: readonly FieldErrorItem[];
}

/** 估值维护表单；提交前执行领域校验并逐字段展示原因。 */
export default class ValuationFormModal extends React.Component<ValuationFormModalProps, ValuationFormModalState> {
  public override state: ValuationFormModalState = { fieldErrors: this.props.fieldErrors };

  private readonly validator = new ValuationDraftValidator();

  /** 同步后端字段错误，并在弹窗重新打开时清理已过期的本地提示。 */
  public override componentDidUpdate(previousProps: ValuationFormModalProps): void {
    if (previousProps.fieldErrors !== this.props.fieldErrors
      || (!previousProps.visible && this.props.visible)) {
      this.setState({ fieldErrors: this.props.fieldErrors });
    }
  }

  /** 更新一个受控字段并移除该字段已过期的提示。 */
  private readonly changeField = <K extends keyof ValuationDraft,>(field: K, value: ValuationDraft[K]): void => {
    this.setState((current) => ({
      fieldErrors: current.fieldErrors.filter((error) => error.field !== field),
    }));
    this.props.onChange({ [field]: value } as Partial<ValuationDraft>);
  };

  /** 文本输入统一转发原始字符串，确保错误输入仍可供更正。 */
  private readonly changeText = (field: keyof ValuationDraft) => (event: ChangeEvent<HTMLInputElement>): void => {
    this.changeField(field, event.target.value);
  };

  /** 返回指定字段的首条中文错误。 */
  private errorFor(field: keyof ValuationDraft): string | undefined {
    return this.state.fieldErrors.find((error) => error.field === field)?.message;
  }

  /** 提交前校验全部字段；失败时保留受控草稿并逐项提示。 */
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
        title="维护估值"
        okText="保存估值"
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
            <Form.Item label="产品代码" required validateStatus={this.errorFor('productCode') ? 'error' : undefined} help={this.errorFor('productCode')}>
              <Input aria-label="产品代码" value={draft.productCode ?? ''} onChange={this.changeText('productCode')} />
            </Form.Item>
            <Form.Item label="估值日期" required validateStatus={this.errorFor('valuationDate') ? 'error' : undefined} help={this.errorFor('valuationDate')}>
              <Input aria-label="估值日期" placeholder="YYYY-MM-DD" value={draft.valuationDate ?? ''} onChange={this.changeText('valuationDate')} />
            </Form.Item>
            <Form.Item label="估值单价" required validateStatus={this.errorFor('unitPrice') ? 'error' : undefined} help={this.errorFor('unitPrice')}>
              <Input aria-label="估值单价" inputMode="decimal" value={draft.unitPrice ?? ''} onChange={this.changeText('unitPrice')} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    );
  }
}
