import { describe, expect, it } from 'vitest';
import AccountDraftValidator from './AccountDraftValidator';

const validator = new AccountDraftValidator();

const validDraft = {
  name: '我的基金账户',
  accountType: 'FUND',
  institution: '示例机构',
  remark: '长期投资',
};

describe('AccountDraftValidator', () => {
  it('允许基金、证券及未来扩展的账户类型编码', () => {
    expect(validator.validateCreate({ ...validDraft, accountType: 'FUND' }).valid).toBe(true);
    expect(validator.validateCreate({ ...validDraft, accountType: 'STOCK' }).valid).toBe(true);
    expect(validator.validateCreate({ ...validDraft, accountType: 'CRYPTO' }).valid).toBe(true);
  });

  it('拒绝必填字段为空并报告字段错误', () => {
    const result = validator.validateCreate({ ...validDraft, name: '  ', accountType: '' });
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.map((error) => error.field)).toEqual(['name', 'accountType']);
  });

  it('允许清空备注并限制备注长度', () => {
    expect(validator.validateRemark(null).valid).toBe(true);
    expect(validator.validateRemark('a'.repeat(255)).valid).toBe(true);
    expect(validator.validateRemark('a'.repeat(256)).fieldErrors[0]?.code).toBe('TOO_LONG');
  });
});
