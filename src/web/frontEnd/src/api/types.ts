// api/types.ts
// 后端 DTO 的前端镜像声明：字段名与 investmentLedger/schemas.py 中 Pydantic 的 camelCase 别名逐字段一致。
// 约定：枚举字段传英文码（中文仅出现在 domain/ledger/labels.ts）；金额与比率一律为十进制字符串
//      （避免 JSON 浮点误差，需求 2.6、3.9）；日期一律为 YYYY-MM-DD。
// 本文件只声明类型，不含任何运行时逻辑，也不做 HTTP 调用（HTTP 出口见 api/ledger.ts）。
import type {
  ProductType,
  TradeDirection,
  SortOrder,
  HoldingSortField,
  LedgerModule,
} from '../domain/ledger/constants';

/** 项目既有响应信封 { code, msg, data }；T 为业务负载类型，镜像后端 ApiResponse[T] */
export interface ApiEnvelope<T> {
  /** 业务状态码，200 为成功，其余由后端 exceptions.py 映射 */
  code: number;
  /** 中文提示语，失败时可直接展示给用户 */
  msg: string;
  /** 业务负载；失败或无返回值的接口（如删除）为 null */
  data: T | null;
}

/** 字段级错误项，与领域层 FieldError 同构，用于回填表单（需求 1.2、3.2） */
export interface FieldErrorItem {
  /** camelCase 字段名，如 unitPrice */
  field: string;
  /** 英文错误码，如 INVALID_SCALE、NOT_IN_ENUM、OUT_OF_RANGE、TOO_LONG */
  code: string;
  /** 中文原因，直接渲染给用户 */
  message: string;
}

/** 统计指标：把「可用性」与「值」显式分开，不可用时 value 为 null，绝不以 0 替代（需求 3.9） */
export interface Metric {
  /** 是否满足该指标公式的定义域；false 时 value 必为 null */
  available: boolean;
  /** 指标值，十进制字符串（金额两位小数，比率高精度）；不可用时为 null */
  value: string | null;
  /** 不可用原因的中文说明，如「缺少最新估值」；available 为 true 时为 null */
  unavailableReason: string | null;
}

/** 一笔交易记录的出参（历史交易表格的行数据，需求 2.12） */
export interface TransactionOut {
  /** 交易主键，仅用于删除定位；界面不渲染、也无按 id 查询接口（需求 2.23） */
  id: number;
  /** 产品类型码 WEALTH/FUND/STOCK，展示时经 PRODUCT_TYPE_LABELS 转中文 */
  productType: ProductType;
  /** 产品名称，<= 100 字符 */
  productName: string;
  /** 产品代码，<= 32 字符 */
  productCode: string;
  /** 交易单价，十进制字符串，恰两位小数 */
  unitPrice: string;
  /** 交易数量，> 0 的整数 */
  quantity: number;
  /** 交易方向码 BUY/SELL，展示时经 TRADE_DIRECTION_LABELS 转中文 */
  direction: TradeDirection;
  /** 交易日期，YYYY-MM-DD */
  tradeDate: string;
}

/** 一个持仓条目的汇总出参（持仓表格 7 列的数据源，需求 2.6） */
export interface HoldingOut {
  /** 产品键之一：产品类型码 */
  productType: ProductType;
  /** 展示名称：取该条目内最新一笔交易的产品名称（交易日期最大、同日 id 最大者） */
  productName: string;
  /** 产品键之二：产品代码 */
  productCode: string;
  /** 持仓（= 持仓市值 = 持仓数量 × 最新估值单价），需求 3.5 */
  position: Metric;
  /** 持仓数量（累计买入数量 − 累计卖出数量）；不作为独立列渲染，仅供核对与提示 */
  positionQuantity: Metric;
  /** 总收益 = 累计卖出金额 + 持仓市值 − 累计买入金额（需求 3.6） */
  totalProfit: Metric;
  /** 总收益率 = 总收益 ÷ 累计买入金额（需求 3.7） */
  totalProfitRate: Metric;
  /** 年化收益率 = (1 + 总收益率)^(365 / 持有天数) − 1（需求 3.8） */
  annualizedRate: Metric;
}

/** 通用分页出参；T 为行数据类型（需求 2.24、2.28、2.29、2.31） */
export interface PageOut<T> {
  /** 当前页的行数据；最后一页可少于 pageSize（需求 2.29） */
  items: T[];
  /** 结果集总条数（分页前） */
  total: number;
  /** 当前页码，1 起 */
  page: number;
  /** 当前页大小 */
  pageSize: number;
  /** 总页数 = ceil(total / pageSize)；为 0 时不存在有效页码（需求 2.31） */
  pageCount: number;
}

/** 投资组合统计出参（需求 3.10-3.12），只聚合具有最新估值的产品 */
export interface PortfolioStatisticsOut {
  /** 总持仓 = Σ 各产品持仓市值 */
  totalPosition: Metric;
  /** 总收益 = Σ 各产品收益 */
  totalProfit: Metric;
  /** 总收益率 = 总收益 ÷ Σ 累计买入金额 */
  totalProfitRate: Metric;
  /** 总年化收益率 = Σ(年化收益率 × 累计买入金额) ÷ Σ 累计买入金额 */
  totalAnnualizedRate: Metric;
}

/** 初始模块决策出参（需求 2.2、2.3） */
export interface InitialModuleOut {
  /** 应默认打开的模块：无任何交易时为 'history'，否则为 'holdings' */
  module: LedgerModule;
}

/** 交易表单草稿（请求负载）：字段允许缺失或 null，代表校验前的中间态（镜像 TransactionCreate） */
export interface TradeDraft {
  /** 产品类型码；未选择时为 null */
  productType?: ProductType | null;
  /** 产品名称，有效范围 1..100 字符 */
  productName?: string | null;
  /** 产品代码，有效范围 1..32 字符 */
  productCode?: string | null;
  /** 交易单价，十进制字符串（不用 number，避免浮点误差与两位小数判定失真） */
  unitPrice?: string | null;
  /** 交易数量；允许 string 以承载 InputNumber 的原始输入 */
  quantity?: string | number | null;
  /** 交易方向码；未选择时为 null */
  direction?: TradeDirection | null;
  /** 交易日期，YYYY-MM-DD（由 dayjs 格式化后写入） */
  tradeDate?: string | null;
}

/** 历史交易查询参数（镜像 TransactionQuery）：所有字段可选，未启用的条件整体省略而非传空值 */
export interface TransactionQueryParams {
  /** 产品类型筛选码（需求 2.16） */
  productType?: ProductType;
  /** 交易方向筛选码（需求 2.16） */
  direction?: TradeDirection;
  /** 日期区间下界（含），YYYY-MM-DD；须与 endDate 同时出现（需求 2.16、2.21） */
  startDate?: string;
  /** 日期区间上界（含），YYYY-MM-DD */
  endDate?: string;
  /** 产品名称包含搜索值，长度 1..100（需求 2.17、2.20） */
  productName?: string;
  /** 产品代码包含搜索值，长度 1..100（需求 2.18、2.20） */
  productCode?: string;
  /** 交易日期排序方向；省略时按 id 升序以保证顺序稳定（需求 2.15） */
  tradeDateOrder?: SortOrder;
  /** 产品历史交易范围的产品类型码；须与 scopeProductCode 同时出现（需求 2.9、2.10） */
  scopeProductType?: ProductType;
  /** 产品历史交易范围的产品代码，长度 1..32（需求 2.9、2.10） */
  scopeProductCode?: string;
  /** 页码，1 起，默认 1（需求 2.28） */
  page?: number;
  /** 页大小，闭区间 1..100，默认 20（需求 2.25、2.26） */
  pageSize?: number;
}

/** 持仓查询参数（镜像 HoldingQuery）：在交易查询之上追加持仓条目的数值排序（需求 2.19） */
export interface HoldingQueryParams extends TransactionQueryParams {
  /** 排序字段：position（持仓）或 totalProfit（总收益）；省略时按首次出现顺序 */
  holdingSortField?: HoldingSortField;
  /** 排序方向；仅在 holdingSortField 存在时生效 */
  holdingSortOrder?: SortOrder;
}
