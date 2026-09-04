import React from 'react';
import { Form, Input, Modal } from 'antd';
import type { FieldErrorItem } from '../../../api/types';
import styles from './index.module.scss';

export interface AccountRemarkModalProps {
  readonly visible: boolean;
  readonly accountName: string | null;
  readonly remark: string;
  readonly fieldErrors: readonly FieldErrorItem[];
  readonly submitting: boolean;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly onCancel: () => void;
}

/** 账户备注唯一编辑入口；不提供名称、类型、机构和启用状态编辑控件。 */
const AccountRemarkModal: React.FC<AccountRemarkModalProps> = ({
  visible,
  accountName,
  remark,
  fieldErrors,
  submitting,
  onChange,
  onSubmit,
  onCancel,
}) => {
  const fieldError = fieldErrors.find((error) => error.field === 'remark')?.message;

  return (
    <Modal
      open={visible}
      title={`编辑备注${accountName ? `：${accountName}` : ''}`}
      okText="保存备注"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={onSubmit}
      onCancel={onCancel}
      destroyOnClose={false}
    >
      <Form className={styles.form} layout="vertical">
        <Form.Item
          label="备注"
          validateStatus={fieldError ? 'error' : ''}
          help={fieldError}
        >
          <Input.TextArea
            value={remark}
            maxLength={255}
            autoSize={{ minRows: 4, maxRows: 8 }}
            onChange={(event) => onChange(event.target.value)}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AccountRemarkModal;
