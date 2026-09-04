import React from 'react';
import { AutoComplete, Form, Input, Modal } from 'antd';
import type { AccountDraft, FieldErrorItem } from '../../../api/types';
import styles from './index.module.scss';

const accountTypeOptions = [
  { value: 'FUND', label: '基金账户（FUND）' },
  { value: 'STOCK', label: '证券账户（STOCK）' },
];

export interface AccountFormModalProps {
  readonly visible: boolean;
  readonly draft: AccountDraft;
  readonly fieldErrors: readonly FieldErrorItem[];
  readonly submitting: boolean;
  readonly onChange: (patch: Partial<AccountDraft>) => void;
  readonly onSubmit: (draft: AccountDraft) => void;
  readonly onCancel: () => void;
}

/** 新建账户弹窗；账户身份字段只在这里创建，后续仅开放备注编辑。 */
const AccountFormModal: React.FC<AccountFormModalProps> = ({
  visible,
  draft,
  fieldErrors,
  submitting,
  onChange,
  onSubmit,
  onCancel,
}) => {
  const errorFor = (field: string): string | undefined =>
    fieldErrors.find((error) => error.field === field)?.message;

  return (
    <Modal
      open={visible}
      title="新建投资账户"
      okText="创建账户"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={() => onSubmit(draft)}
      onCancel={onCancel}
      destroyOnClose={false}
    >
      <Form className={styles.form} layout="vertical">
        <div className={styles.grid}>
          <Form.Item
            label="账户名称"
            required
            validateStatus={errorFor('name') ? 'error' : ''}
            help={errorFor('name')}
          >
            <Input
              value={draft.name}
              placeholder="例如：我的长期基金账户"
              maxLength={100}
              onChange={(event) => onChange({ name: event.target.value })}
            />
          </Form.Item>
          <Form.Item
            label="账户类型"
            required
            validateStatus={errorFor('accountType') ? 'error' : ''}
            help={errorFor('accountType')}
          >
            <AutoComplete
              value={draft.accountType}
              options={accountTypeOptions}
              placeholder="选择或输入类型编码"
              onChange={(value) => onChange({ accountType: value })}
            />
          </Form.Item>
          <Form.Item
            label="机构/平台"
            validateStatus={errorFor('institution') ? 'error' : ''}
            help={errorFor('institution')}
          >
            <Input
              value={draft.institution}
              placeholder="例如：某基金公司或券商"
              maxLength={100}
              onChange={(event) => onChange({ institution: event.target.value })}
            />
          </Form.Item>
          <Form.Item
            className={styles.fullWidth}
            label="备注"
            validateStatus={errorFor('remark') ? 'error' : ''}
            help={errorFor('remark')}
          >
            <Input.TextArea
              value={draft.remark}
              placeholder="可选"
              maxLength={255}
              autoSize={{ minRows: 3, maxRows: 6 }}
              onChange={(event) => onChange({ remark: event.target.value })}
            />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
};

export default AccountFormModal;
