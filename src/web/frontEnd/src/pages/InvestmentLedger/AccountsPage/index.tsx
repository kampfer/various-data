import React from 'react';
import { Button, message } from 'antd';
import { connect } from 'react-redux';
import type { RootState, AppDispatch } from '../../../store';
import type { AccountCreatePayload, AccountDraft } from '../../../api/types';
import AccountFormModal from '../../../components/InvestmentLedger/AccountFormModal';
import AccountList from '../../../components/InvestmentLedger/AccountList';
import AccountRemarkModal from '../../../components/InvestmentLedger/AccountRemarkModal';
import {
  changeAccountDraft,
  changeAccountRemark,
  closeAccountForm,
  closeAccountRemarkForm,
  openAccountForm,
  openAccountRemarkForm,
} from '../../../store/ledger/ledgerSlice';
import { createAccount, fetchAccounts, updateAccountRemark, updateAccountStatus } from '../../../store/ledger/thunks';
import type { LedgerState } from '../../../store/ledger/types';
import { rejectionMessage } from '../pageUtils';
import styles from '../index.module.scss';

interface StateProps {
  readonly accounts: LedgerState['accounts'];
  readonly accountForm: LedgerState['accountForm'];
  readonly accountRemarkForm: LedgerState['accountRemarkForm'];
}

interface DispatchProps {
  readonly dispatch: AppDispatch;
}

type AccountsPageProps = StateProps & DispatchProps;

/** 投资账户管理容器：负责加载账户以及协调创建和备注更新两个写入用例。 */
export class AccountsPageContainer extends React.Component<AccountsPageProps> {
  public override componentDidMount(): void {
    void this.props.dispatch(fetchAccounts());
  }

  public override componentDidUpdate(previousProps: AccountsPageProps): void {
    if (
      this.props.accounts.error !== null
      && this.props.accounts.error !== previousProps.accounts.error
    ) {
      void message.error(this.props.accounts.error);
    }
  }

  private readonly handleCreate = (draft: AccountDraft): void => {
    const payload: AccountCreatePayload = {
      name: draft.name,
      accountType: draft.accountType,
      institution: draft.institution.trim() || null,
      remark: draft.remark.trim() || null,
    };
    void this.props.dispatch(createAccount(payload)).unwrap()
      .then(() => message.success('投资账户已创建'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '账户创建失败')));
  };

  private readonly handleEditRemark = (account: StateProps['accounts']['items'][number]): void => {
    this.props.dispatch(openAccountRemarkForm({ id: account.id, remark: account.remark }));
  };

  private readonly handleToggleStatus = (account: StateProps['accounts']['items'][number]): void => {
    const nextIsActive = !account.isActive;
    void this.props.dispatch(updateAccountStatus({
      accountId: account.id,
      payload: { isActive: nextIsActive },
    })).unwrap()
      .then(() => message.success(nextIsActive ? '账户已启用' : '账户已停用'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '账户状态更新失败')));
  };

  private readonly handleSaveRemark = (): void => {
    const { accountId, remark } = this.props.accountRemarkForm;
    if (accountId === null) return;
    void this.props.dispatch(updateAccountRemark({
      accountId,
      payload: { remark: remark.trim() || null },
    })).unwrap()
      .then(() => message.success('账户备注已保存'))
      .catch((error: unknown) => message.error(rejectionMessage(error, '备注保存失败')));
  };

  private readonly accountNameForRemark = (): string | null => {
    const account = this.props.accounts.items.find(
      (item) => item.id === this.props.accountRemarkForm.accountId,
    );
    return account?.name ?? null;
  };

  public override render(): React.ReactNode {
    const { accounts, accountForm, accountRemarkForm } = this.props;
    return (
      <div className={styles.modulePage}>
        <div className={styles.moduleHeader}>
          <h2 className={styles.moduleTitle}>账户管理</h2>
          <Button type="primary" onClick={() => this.props.dispatch(openAccountForm())}>
            新建账户
          </Button>
        </div>
        <AccountList
          items={accounts.items}
          loading={accounts.loading}
          updatingId={accounts.updatingId}
          onEditRemark={this.handleEditRemark}
          onToggleStatus={this.handleToggleStatus}
        />
        <AccountFormModal
          visible={accountForm.visible}
          draft={accountForm.draft}
          fieldErrors={accountForm.fieldErrors}
          submitting={accountForm.submitting}
          onChange={(patch) => this.props.dispatch(changeAccountDraft(patch))}
          onSubmit={this.handleCreate}
          onCancel={() => this.props.dispatch(closeAccountForm())}
        />
        <AccountRemarkModal
          visible={accountRemarkForm.visible}
          accountName={this.accountNameForRemark()}
          remark={accountRemarkForm.remark}
          fieldErrors={accountRemarkForm.fieldErrors}
          submitting={accountRemarkForm.submitting}
          onChange={(value) => this.props.dispatch(changeAccountRemark(value))}
          onSubmit={this.handleSaveRemark}
          onCancel={() => this.props.dispatch(closeAccountRemarkForm())}
        />
      </div>
    );
  }
}

const mapStateToProps = (state: RootState): StateProps => ({
  accounts: state.ledger.accounts,
  accountForm: state.ledger.accountForm,
  accountRemarkForm: state.ledger.accountRemarkForm,
});

const mapDispatchToProps = (dispatch: AppDispatch): DispatchProps => ({ dispatch });

const ConnectedAccountsPage = connect<StateProps, DispatchProps, object, RootState>(
  mapStateToProps,
  mapDispatchToProps,
)(AccountsPageContainer);

export default ConnectedAccountsPage;
