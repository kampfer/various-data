// store/index.ts
// Redux 根装配：保留三个既有状态分支，并注册投资交易账本状态分支。
import { configureStore } from '@reduxjs/toolkit';
import type { Reducer } from 'redux';
import news from './reducers/news.js';
import stock from './reducers/stock.js';
import crawlers from './reducers/crawlers.js';
import ledger from './ledger/ledgerSlice';

/** 应用唯一 Redux store；configureStore 保留 thunk 支持并启用开发期检查。 */
const store = configureStore({
  reducer: {
    // checkJs 关闭时旧 JS reducer 的空数组会被推导为 never[]；转换仅修正静态类型，不改变运行时行为。
    news: news as Reducer,
    stock: stock as Reducer,
    crawlers: crawlers as Reducer,
    ledger,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      // 旧模块会保存 dayjs 实例；保持原状态形状并仅豁免这些已知路径与对应旧 action。
      serializableCheck: {
        ignoredActions: ['SET_FILTERS'],
        ignoredPaths: ['news.filters.period', 'stock.zoomStart', 'stock.zoomEnd'],
      },
      immutableCheck: {
        ignoredPaths: ['news.filters.period', 'stock.zoomStart', 'stock.zoomEnd'],
      },
    }),
});

/** Redux 根状态类型，由实际 reducer 映射自动推导。 */
export type RootState = ReturnType<typeof store.getState>;

/** Redux dispatch 类型，包含 thunk dispatch 能力。 */
export type AppDispatch = typeof store.dispatch;

export default store;
