// types/global.d.ts —— 全局环境声明（无 import/export 顶层语句，故为全局脚本）

/** CSS Modules（Sass）：webpack 的 modules.auto 只对 *.module.scss 生效，故默认导出为「原类名 → 编译后类名」映射 */
declare module '*.module.scss' {
    /** 只读的类名映射表；键为源文件中书写的类名 */
    const classes: { readonly [key: string]: string };
    export default classes;
}

/** CSS Modules（原生 css）：同上，便于日后新增 *.module.css */
declare module '*.module.css' {
    const classes: { readonly [key: string]: string };
    export default classes;
}

// 既有全局样式以副作用方式导入（import './index.css'），无默认导出，声明为无形状模块即可
declare module '*.css';
declare module '*.scss';


/** 天天基金 FundCode_utf8.js 注入的基金代码表记录。 */
type EastmoneyFundRecord = readonly [
    fundCode: string,
    fundPinyinInitials: string,
    fundName: string,
    ...additionalFields: unknown[],
];

interface Window {
    /** FundCode_utf8.js 中的全局基金代码表；脚本未加载时可能不存在。 */
    r?: readonly EastmoneyFundRecord[];
}
