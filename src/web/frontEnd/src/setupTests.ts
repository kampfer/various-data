/// <reference types="vitest/globals" />
// 全局测试引导（投资交易账本 spec 任务 9.3）
// 引入 jest-dom 的 vitest 适配入口，为 expect 注册 DOM 语义断言（toBeInTheDocument 等）。
import '@testing-library/jest-dom/vitest';

/** jsdom 未实现 matchMedia；antd 响应式组件在测试环境中依赖该浏览器 API。 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
});
