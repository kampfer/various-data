// 调度器后台管理的开发构建配置：3001 端口，/api 代理到嵌入式管理服务。

import config from './webpack.config.js';

export default Object.assign({}, config, {
    mode: 'development',
    devServer: {
        open: false,
        port: 3001,
        hot: true,
        historyApiFallback: false,
        proxy: [
            {
                context: ['/api'],
                target: 'http://127.0.0.1:8787',
                changeOrigin: true,
            },
        ],
    },
});
