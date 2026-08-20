import React from 'react';
import { DatePicker, Form, Input, Modal, Select } from 'antd';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import type { ChangeEvent } from 'react';
import type { FieldErrorItem, FundSearchOut, TradeDraft } from '../../../api/types';
import type { ProductType, TradeDirection } from '../../../domain/ledger/constants';
import FundSearchController from '../../../domain/ledger/FundSearchController';
import TradeDraftValidator from '../../../domain/ledger/TradeDraftValidator';
import { productTypeOptions, tradeDirectionOptions, TRADE_VALUE_LABELS } from '../../../domain/ledger/labels';
import FundSearchResults from '../FundSearchResults';
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
interface TradeFormModalState { readonly fieldErrors: readonly FieldErrorItem[]; readonly searchResults: readonly FundSearchOut[]; readonly searching: boolean; /** 是否已对当前输入发起过搜索请求；用于搜索后无结果时仍展示空态浮动框（需求 5.4） */ readonly hasSearched: boolean; }
/** 新建交易表单：字段状态使用 canonical 名称，标签仅随产品类型渲染。产品类型为基金时挂载基金搜索辅助（需求 5）。 */
export default class TradeFormModal extends React.Component<TradeFormModalProps, TradeFormModalState> {
  public override state: TradeFormModalState = { fieldErrors: this.props.fieldErrors, searchResults: [], searching: false, hasSearched: false };

  /**
   * 基金搜索控制器：封装 500ms 防抖与请求竞态保护（需求 5.3、5.6）。
   * 控制器只通过回调把结果与加载态写回组件局部 state，不接触 Redux、不写入交易草稿。
   *
   * hasSearched 维护策略（需求 5.4：搜索后无结果仍展示空态浮动框）：
   *   - loading 由 false 变 true 表示已对非空输入开始防抖/请求，置 hasSearched=true；
   *   - loading 由 true 变 false（搜索完成）**不动** hasSearched，让无结果时空态浮动框保持可见；
   *   - 输入清空、选中回填、弹窗关闭、切换为非基金类型时由调用方经 resetSearch() 显式置 hasSearched=false。
   */
  private readonly fundSearchController = new FundSearchController({
    onResults: (results) => this.setState({ searchResults: results }),
    onLoadingChange: (loading) => {
      if (loading) {
        // 进入防抖/请求：标记已搜索，使搜索完成无结果时浮动框仍可见
        this.setState({ searching: true, hasSearched: true });
      } else {
        // 搜索完成或输入清空：仅复位加载态，hasSearched 由调用方按需重置
        this.setState({ searching: false });
      }
    },
  });

  /** 选中结果回填的同帧标记：跳过本次输入变化触发的搜索（需求 5.5）。 */
  private justSelected = false;

  private readonly validator = new TradeDraftValidator();

  public override componentWillUnmount(): void {
    // 弹窗组件卸载时销毁控制器，确保在飞请求不再回调 setState
    this.fundSearchController.dispose();
  }

  /**
   * 重置搜索态：把 hasSearched 置 false 并取消挂起请求/清空结果。
   *
   * 用于以下需要丢弃搜索上下文并隐藏浮动框的场景：
   *   - 输入清空（需求 5.3 空输入不发请求且清空结果）；
   *   - 选中结果回填（需求 5.5）；
   *   - 弹窗关闭、切换为非基金类型（需求 5.1）。
   *
   * setState({ hasSearched: false }) 先于 fundSearchController.search('') 调用，
   * 后者同步触发的 onLoadingChange(false) 回调**不动 hasSearched**，
   * 因此 hasSearched 在最终批处理提交时保持 false，浮动框按预期隐藏。
   */
  private readonly resetSearch = (): void => {
    this.setState({ hasSearched: false });
    this.fundSearchController.search('');
  };

  public override componentDidUpdate(previousProps: TradeFormModalProps): void {
    // 1) 同步字段级错误（既有逻辑）：错误引用变化或弹窗刚打开时刷新
    if (previousProps.fieldErrors !== this.props.fieldErrors || (!previousProps.visible && this.props.visible)) {
      this.setState({ fieldErrors: this.props.fieldErrors });
    }

    // 2) 基金搜索编排：仅在弹窗可见时运行
    const { draft, visible } = this.props;
    const prevDraft = previousProps.draft;

    // 弹窗关闭：清空搜索态并取消挂起请求，避免下次打开残留旧结果
    if (previousProps.visible && !visible) {
      this.justSelected = false;
      this.resetSearch();
      return;
    }
    if (!visible) return;

    // 选中结果回填的同帧：跳过搜索编排，结果已在 handleSelectFund 中清空
    if (this.justSelected) {
      this.justSelected = false;
      return;
    }

    const isFund = draft.productType === 'FUND';
    const wasFund = prevDraft.productType === 'FUND';

    // 切换到非基金类型：清空搜索态并不再发起请求（需求 5.1）
    if (wasFund && !isFund) {
      this.resetSearch();
      return;
    }
    if (!isFund) return;

    // 产品类型为基金：根据产品名称或产品代码的最新变化触发防抖搜索
    const prevName = prevDraft.productName ?? '';
    const currName = draft.productName ?? '';
    const prevCode = prevDraft.productCode ?? '';
    const currCode = draft.productCode ?? '';

    if (currName !== prevName && currName.length > 0) {
      // 产品名称变化且非空：以名称为关键词搜索
      this.fundSearchController.search(currName);
    } else if (currCode !== prevCode && currCode.length > 0) {
      // 产品代码变化且非空：以代码为关键词搜索
      this.fundSearchController.search(currCode);
    } else if (currName !== prevName || currCode !== prevCode) {
      // 任一字段被清空：清空搜索结果与 hasSearched，隐藏浮动框（需求 5.3 空输入不发请求）
      this.resetSearch();
    }
  }

  private readonly changeField = <K extends keyof TradeDraft,>(field: K, value: TradeDraft[K]): void => { this.setState((current) => ({ fieldErrors: current.fieldErrors.filter((error) => error.field !== field) })); this.props.onChange({ [field]: value } as Partial<TradeDraft>); };
  private readonly changeText = (field: keyof TradeDraft) => (event: ChangeEvent<HTMLInputElement>): void => this.changeField(field, event.target.value);
  /** DatePicker 选择后把 Dayjs 规范化为 YYYY-MM-DD 文本，保持草稿仍为可序列化字符串。 */
  private readonly changeTradeDate = (value: Dayjs | null): void => this.changeField('tradeDate', value === null ? null : value.format(TRADE_DATE_FORMAT));
  private errorFor(field: keyof TradeDraft): string | undefined { return this.state.fieldErrors.find((error) => error.field === field)?.message; }

  /**
   * 选中某条基金搜索结果：回填产品名称与产品代码并清空结果区域（需求 5.5）。
   * 通过 justSelected 标记使本次回填触发的输入变化不再发起搜索。
   */
  private readonly handleSelectFund = (fundName: string, fundCode: string): void => {
    this.justSelected = true;
    // 取消挂起请求、清空结果与 hasSearched，避免回填后再触发搜索或回放旧结果
    this.resetSearch();
    this.props.onChange({ productName: fundName, productCode: fundCode });
  };

  private readonly submit = (): void => { const result = this.validator.validate(this.props.draft); this.setState({ fieldErrors: result.fieldErrors }); if (result.valid) this.props.onSubmit(this.props.draft); };
  public override render(): React.ReactNode {
    const { visible, draft, submitting, onCancel } = this.props;
    const type = draft.productType ?? 'FUND'; const labels = TRADE_VALUE_LABELS[type];
    // 浮动下拉框显示条件（需求 5.1、5.4）：
    //   - productType 必须为 FUND；非 FUND 一律不显示；
    //   - searching=true（正在防抖/请求）→ 显示加载态浮动框；
    //   - searchResults 非空 → 显示结果列表浮动框；
    //   - hasSearched=true 且无加载、无结果 → 搜索后无匹配，显示空态浮动框。
    //   未输入（hasSearched=false）不显示，避免空白浮动框遮挡其他表单项。
    const showFundSearch =
      draft.productType === 'FUND' &&
      (this.state.searching ||
        this.state.searchResults.length > 0 ||
        this.state.hasSearched);
    return <Modal open={visible} title="新建交易记录" okText="创建交易" cancelText="取消" confirmLoading={submitting} onOk={this.submit} onCancel={onCancel}>
      <Form className={styles.form} layout="vertical" autoComplete="off"><div className={styles.grid}>
        <Form.Item label="产品类型" required validateStatus={this.errorFor('productType') ? 'error' : undefined} help={this.errorFor('productType')}><Select<ProductType> aria-label="产品类型" className={styles.fullWidth} virtual={false} placeholder="请选择产品类型" value={draft.productType ?? undefined} options={[...productTypeOptions()]} onChange={(value) => this.changeField('productType', value)} /></Form.Item>
        <Form.Item label="交易方向" required validateStatus={this.errorFor('direction') ? 'error' : undefined} help={this.errorFor('direction')}><Select<TradeDirection> aria-label="交易方向" className={styles.fullWidth} virtual={false} placeholder="请选择交易方向" value={draft.direction ?? undefined} options={[...tradeDirectionOptions()]} onChange={(value) => this.changeField('direction', value)} /></Form.Item>
        <div className={styles.fundFieldsRow}>
          <Form.Item label="产品名称" required validateStatus={this.errorFor('productName') ? 'error' : undefined} help={this.errorFor('productName')}><Input aria-label="产品名称" allowClear value={draft.productName ?? ''} onChange={this.changeText('productName')} /></Form.Item>
          <Form.Item label="产品代码" required validateStatus={this.errorFor('productCode') ? 'error' : undefined} help={this.errorFor('productCode')}><Input aria-label="产品代码" allowClear value={draft.productCode ?? ''} onChange={this.changeText('productCode')} /></Form.Item>
          {showFundSearch && (
            <FundSearchResults loading={this.state.searching} results={this.state.searchResults} onSelect={this.handleSelectFund} />
          )}
        </div>
        <Form.Item label={labels.price} required validateStatus={this.errorFor('transactionPrice') ? 'error' : undefined} help={this.errorFor('transactionPrice')}><Input aria-label={labels.price} inputMode="decimal" allowClear value={draft.transactionPrice ?? ''} onChange={this.changeText('transactionPrice')} /></Form.Item>
        <Form.Item label={labels.quantity} required validateStatus={this.errorFor('transactionQuantity') ? 'error' : undefined} help={this.errorFor('transactionQuantity')}><Input aria-label={labels.quantity} inputMode="decimal" allowClear value={draft.transactionQuantity ?? ''} onChange={this.changeText('transactionQuantity')} /></Form.Item>
        <Form.Item label="交易日期" required validateStatus={this.errorFor('tradeDate') ? 'error' : undefined} help={this.errorFor('tradeDate')}><DatePicker aria-label="交易日期" className={styles.fullWidth} format={TRADE_DATE_FORMAT} value={toTradeDateDayjs(draft.tradeDate)} onChange={this.changeTradeDate} /></Form.Item>
      </div></Form></Modal>;
  }
}
