// domain/ledger/LedgerQueryState.ts
// 浏览状态（筛选 + 搜索 + 排序 + 分页 + 产品范围）的不可变值对象：
// 所有变换方法返回新实例；导航重置由 default/defaultWithScope 提供，查询条件变更的页码规则在此唯一实现。
import type { ProductType, TradeDirection, LedgerModule, SortOrder, HoldingSortField } from './constants';
import { DEFAULT_PAGE_SIZE } from './constants';

/**
 * 可序列化的查询快照：存进 redux state 的形状（纯数据，无类实例、无 dayjs 对象）。
 * 所有「未启用」的条件统一以 null 表示，便于 toParams() 直接省略该参数。
 */
export interface LedgerQuerySnapshot {
  /** 产品类型筛选码；null=未启用该筛选（需求 2.16） */
  readonly productType: ProductType | null;
  /** 交易方向筛选码；null=未启用（需求 2.16） */
  readonly direction: TradeDirection | null;
  /** 交易日期范围起始，YYYY-MM-DD，闭区间下界；与 endDate 必须成对（需求 2.16、2.21） */
  readonly startDate: string | null;
  /** 交易日期范围结束，YYYY-MM-DD，闭区间上界；须 >= startDate（需求 2.16、2.21） */
  readonly endDate: string | null;
  /** 产品名称搜索值，语义为「包含」匹配，长度 1..100；null=未启用（需求 2.17、2.18、2.20） */
  readonly productName: string | null;
  /** 产品代码搜索值，语义为「包含」匹配，长度 1..100；null=未启用（需求 2.17、2.18、2.20） */
  readonly productCode: string | null;
  /** 确认日期排序方向；null=使用后端默认确认日期降序（需求 2.15） */
  readonly tradeDateOrder: SortOrder | null;
  /** 持仓条目排序字段；null=未启用数值排序，此时按首次出现顺序（需求 2.15、2.19） */
  readonly holdingSortField: HoldingSortField | null;
  /** 持仓条目排序方向；仅在 holdingSortField 非 null 时有意义（需求 2.19） */
  readonly holdingSortOrder: SortOrder | null;
  /** 当前页码，1 起；有效范围 1..pageCount（需求 2.28、2.30） */
  readonly page: number;
  /** 当前页大小，闭区间 1..100（需求 2.24、2.25） */
  readonly pageSize: number;
  /** 产品历史交易范围的产品代码（需求 2.9、2.10）；null=未启用范围 */
  readonly scopeProductCode: string | null;
}

/**
 * 产品历史交易范围：从持仓进入历史交易时携带的范围参数。
 * 产品名称仅供页面标题展示，不进入后端查询（需求 2.5、2.9）。
 */
export interface ProductScope {
  /** 产品代码（范围精确匹配） */
  readonly productCode: string;
  /** 产品名称（仅用于展示） */
  readonly productName: string;
}

/**
 * 发往后端的 query 参数：键取自快照字段名（camelCase），
 * 值为字符串或数字（枚举传英文码，日期传 YYYY-MM-DD）；未启用的字段整体省略而非传 null。
 */
export type LedgerQueryParams = Partial<Record<keyof LedgerQuerySnapshot, string | number>>;

/**
 * 各模块「预设页大小」（需求「默认浏览状态」定义）。
 * 当前两个模块取值一致，独立成表以便后续按模块分化而不改动调用方。
 */
const MODULE_DEFAULT_PAGE_SIZE: Record<LedgerModule, number> = {
  history: DEFAULT_PAGE_SIZE,
  holdings: DEFAULT_PAGE_SIZE,
};

/** 产品历史交易范围字段：不参与「是否为默认浏览状态」的比较（需求 2.9） */
const SCOPE_KEYS: readonly (keyof LedgerQuerySnapshot)[] = ['scopeProductCode'];

/** 可由 withFilters 修改的查询条件；页码、页大小和产品范围由专门方法/导航意图管理。 */
const FILTER_KEYS: readonly (keyof LedgerQuerySnapshot)[] = [
  'productType',
  'direction',
  'startDate',
  'endDate',
  'productName',
  'productCode',
  'tradeDateOrder',
  'holdingSortField',
  'holdingSortOrder',
];

/** 浏览状态值对象：构造私有，只能经 default / defaultWithScope / from 创建 */
export default class LedgerQueryState {
  /**
   * @param snapshot 内部持有的纯数据快照；构造后连同实例一起冻结，保证真正不可变
   */
  private constructor(private readonly snapshot: LedgerQuerySnapshot) {
    Object.freeze(this.snapshot);
    Object.freeze(this);
  }

  /**
   * 构造模块的默认浏览状态：全部筛选/搜索/排序为 null，pageSize=DEFAULT_PAGE_SIZE，page=1，无产品范围。
   * @param module 目标模块，决定默认排序字段的取舍（当前两模块默认值一致，保留参数以便后续分化）
   * @returns 满足需求「默认浏览状态」定义的新实例
   */
  static default(module: LedgerModule): LedgerQueryState {
    return new LedgerQueryState({
      productType: null,
      direction: null,
      startDate: null,
      endDate: null,
      productName: null,
      productCode: null,
      tradeDateOrder: null,
      holdingSortField: null,
      holdingSortOrder: null,
      page: 1,
      pageSize: MODULE_DEFAULT_PAGE_SIZE[module],
      scopeProductCode: null,
    });
  }

  /**
   * 构造「默认浏览状态 + 产品历史交易范围」：除 scopeProductCode 外与 default(module) 完全相同。
   * @param scope 来源持仓条目的产品范围（productCode 用于查询，productName 仅用于页面标题展示）
   * @returns 需求 2.9 要求的状态（不继承任何此前条件）
   */
  static defaultWithScope(module: LedgerModule, scope: ProductScope): LedgerQueryState {
    if (module !== 'history') {
      throw new Error('产品历史交易范围仅适用于历史交易记录模块');
    }
    return new LedgerQueryState({
      ...LedgerQueryState.default(module).snapshot,
      scopeProductCode: scope.productCode,
    });
  }

  /**
   * 从 redux 中的纯数据快照还原领域对象（reducer 与选择器的入口）。
   * @param snapshot 已存在的快照，不会被修改（内部持有其浅拷贝，避免冻结调用方对象）
   */
  static from(snapshot: LedgerQuerySnapshot): LedgerQueryState {
    return new LedgerQueryState(LedgerQueryState.normalizeScope(snapshot));
  }

  /**
   * 合并筛选/搜索/排序补丁。
   * @param patch 仅包含待变更字段；未出现的字段保持原值
   * @returns 新实例；**不变量：只要 patch 非空即把 page 置为 1**（需求 2.27）
   */
  withFilters(patch: Partial<LedgerQuerySnapshot>): LedgerQueryState {
    // 范围不是普通筛选条件：它只能由 holding-scope 导航通过 defaultWithScope 注入。
    const effective = LedgerQueryState.pickDefined(patch, FILTER_KEYS);
    // 空补丁不构成「更改条件」，浏览状态（含页码）原样保持
    if (Object.keys(effective).length === 0) return this;
    return new LedgerQueryState({ ...this.snapshot, ...effective, page: 1 });
  }

  /**
   * 切换页大小。
   * @param size 已由 QueryInputValidator 校验通过的 1..100 整数
   * @returns 新实例；**不变量：page 置为 1**（需求 2.25）
   */
  withPageSize(size: number): LedgerQueryState {
    return new LedgerQueryState({ ...this.snapshot, pageSize: size, page: 1 });
  }

  /**
   * 仅翻页。
   * @param page 已校验的有效页码
   * @returns 新实例；**不变量：除 page 外所有字段逐字段相等**（需求 2.28）
   */
  withPage(page: number): LedgerQueryState {
    return new LedgerQueryState({ ...this.snapshot, page });
  }

  /**
   * 判断当前状态是否等于该模块的默认浏览状态（产品范围字段不参与比较）。
   * 供属性测试断言重置不变量、以及「重置」按钮的禁用判定使用。
   */
  isDefault(module: LedgerModule): boolean {
    const base = LedgerQueryState.default(module).snapshot;
    return (Object.keys(base) as (keyof LedgerQuerySnapshot)[])
      .filter((key) => !SCOPE_KEYS.includes(key))
      .every((key) => this.snapshot[key] === base[key]);
  }

  /** 导出内部快照，用于写回 redux；返回的对象已冻结，调用方不能改 */
  toSnapshot(): LedgerQuerySnapshot {
    return this.snapshot;
  }

  /** 序列化为后端 query 参数：跳过所有值为 null 的字段，枚举按英文码原样输出 */
  toParams(): LedgerQueryParams {
    const params: LedgerQueryParams = {};
    (Object.keys(this.snapshot) as (keyof LedgerQuerySnapshot)[]).forEach((key) => {
      const value = this.snapshot[key];
      if (value === null) return;
      params[key] = value;
    });
    return params;
  }

  /**
   * 规范化产品历史交易范围：将 undefined 归一为 null，避免持久化边界引入的半空值。
   */
  private static normalizeScope(snapshot: LedgerQuerySnapshot): LedgerQuerySnapshot {
    if (snapshot.scopeProductCode === undefined) {
      return { ...snapshot, scopeProductCode: null };
    }
    return { ...snapshot };
  }

  /**
   * 剔除补丁中值为 undefined 的键，并限制为普通查询条件字段。
   * `Partial` 允许显式传 undefined，但那语义上等于「未变更」，不能覆盖原值也不应触发页码重置。
   */
  private static pickDefined(
    patch: Partial<LedgerQuerySnapshot>,
    allowedKeys: readonly (keyof LedgerQuerySnapshot)[],
  ): Partial<LedgerQuerySnapshot> {
    const result: Record<string, unknown> = {};
    allowedKeys.forEach((key) => {
      const value = patch[key];
      if (value !== undefined) result[key] = value;
    });
    return result as Partial<LedgerQuerySnapshot>;
  }
}
