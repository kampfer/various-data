// 前端测试环境配置（投资交易账本 spec 任务 9.3）
// 仅服务于测试：vitest 通过 esbuild 原生转译 .ts / .tsx，不复用 webpack 的 babel 管线。
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vitest/config';

const ROOT_PATH = path.dirname(fileURLToPath(import.meta.url));
const FRONT_END_SRC = path.join(ROOT_PATH, 'src/web/frontEnd/src');

export default defineConfig({
    resolve: {
        alias: {
            // 与 tsconfig.json paths 及 webpack resolve.alias 保持一致
            '@ledger': FRONT_END_SRC,
        },
    },
    test: {
        // 组件测试需要 DOM：@testing-library/react 依赖 document / window
        environment: 'jsdom',
        // 允许测试文件直接使用 describe / it / expect / afterEach，
        // 同时让 @testing-library/react 的自动 cleanup 生效
        globals: true,
        // 注册 jest-dom 断言（toBeInTheDocument 等）
        setupFiles: [path.join(FRONT_END_SRC, 'setupTests.ts')],
        // 只收集前端源码目录内的测试文件，避免扫描 node_modules 与 Python 代码
        include: ['src/web/frontEnd/src/**/*.test.{ts,tsx}'],
        css: {
            modules: {
                // 不做 CSS 编译，*.module.scss 的导入返回未加哈希的原始类名，
                // 便于示例测试断言「样式经 CSS Modules class 生效」
                classNameStrategy: 'non-scoped',
            },
        },
        // 单次执行模式：watch 交由开发者显式开启，CI/脚本一律跑完即退出
        watch: false,
        // 属性测试任务尚未落地前，空测试集不应让 `npm test` 失败
        passWithNoTests: true,
        clearMocks: true,
        restoreMocks: true,
    },
});
