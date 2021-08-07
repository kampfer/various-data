// 参考配置：
// https://raw.githubusercontent.com/kampfer/gltf2-viewer/master/scripts/webpack.dev.config.js

import config from './webpack.config.js';

let devConfig = Object.assign(config, {
    mode: 'development'
});

export default devConfig;
