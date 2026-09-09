// 参考配置：
// https://raw.githubusercontent.com/kampfer/gltf2-viewer/master/scripts/webpack.dev.config.js

import config from './webpack.config.js';

let devConfig = Object.assign(config, {
    mode: 'development',
    devServer: {
        port: 3000,
        hot: true,                      // 开启 HMR
        historyApiFallback: true,       // 支持 SPA 路由
        proxy: [{
            context: ['/api'],        // 匹配所有 /api 开头的请求
            target: 'http://localhost:8000',
            changeOrigin: true,
        }],
    },
});

export default devConfig;
