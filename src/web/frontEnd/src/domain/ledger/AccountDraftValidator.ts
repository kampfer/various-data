import type { AccountDraft } from '../../api/types';
import type { FieldError } from './TradeDraftValidator';

const MAX_ACCOUNT_NAME_LENGTH = 100;
const MAX_ACCOUNT_TYPE_LENGTH = 32;
const MAX_INSTITUTION_LENGTH = 100;
const MAX_REMARK_LENGTH = 255;

export interface AccountValidationResult {
  readonly valid: boolean;
  readonly fieldErrors: readonly FieldError[];
}

const charLength = (value: string): number => Array.from(value).length;

/** 账户创建及备注编辑共用的纯函数校验器；不修改用户输入。 */
export default class AccountDraftValidator {
  public validateCreate(draft: AccountDraft): AccountValidationResult {
    const fieldErrors: FieldError[] = [];
    this.checkRequired(fieldErrors, 'name', draft.name, '账户名称', MAX_ACCOUNT_NAME_LENGTH);
    this.checkRequired(fieldErrors, 'accountType', draft.accountType, '账户类型', MAX_ACCOUNT_TYPE_LENGTH);
    this.checkOptional(fieldErrors, 'institution', draft.institution, '机构/平台', MAX_INSTITUTION_LENGTH);
    this.checkOptional(fieldErrors, 'remark', draft.remark, '备注', MAX_REMARK_LENGTH);
    return { valid: fieldErrors.length === 0, fieldErrors };
  }

  public validateRemark(value: string | null): AccountValidationResult {
    const fieldErrors: FieldError[] = [];
    if (value !== null && charLength(value) > MAX_REMARK_LENGTH) {
      fieldErrors.push({
        field: 'remark',
        code: 'TOO_LONG',
        message: `备注不能超过 ${MAX_REMARK_LENGTH} 个字符`,
      });
    }
    return { valid: fieldErrors.length === 0, fieldErrors };
  }

  private checkRequired(
    errors: FieldError[],
    field: string,
    value: string,
    label: string,
    maxLength: number,
  ): void {
    if (value.trim().length === 0) {
      errors.push({ field, code: 'REQUIRED', message: `${label}不能为空` });
      return;
    }
    if (charLength(value) > maxLength) {
      errors.push({ field, code: 'TOO_LONG', message: `${label}不能超过 ${maxLength} 个字符` });
    }
  }

  private checkOptional(
    errors: FieldError[],
    field: string,
    value: string,
    label: string,
    maxLength: number,
  ): void {
    if (charLength(value) > maxLength) {
      errors.push({ field, code: 'TOO_LONG', message: `${label}不能超过 ${maxLength} 个字符` });
    }
  }
}
