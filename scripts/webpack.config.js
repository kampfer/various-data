// 参考配置：
// https://raw.githubusercontent.com/kampfer/gltf2-viewer/master/scripts/webpack.config.js

import { CleanWebpackPlugin } from 'clean-webpack-plugin';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import path from 'path';
import { ROOT_PATH } from '../src/constants.js';
import CopyPlugin from 'copy-webpack-plugin';

export default {
    entry: path.join(ROOT_PATH, 'src/web/js/main.js'),
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /(node_modules|bower_components)/,
                loader: 'babel-loader'
            },
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            }
        ]
    },
    plugins: [
        new CleanWebpackPlugin(),
        new HtmlWebpackPlugin({
            filename: 'index.html',
            template: path.join(ROOT_PATH, 'src/web/index.html'),
            inject: 'body'
        }),
        new CopyPlugin({
            patterns: [
                {
                    from: path.join(ROOT_PATH, 'src/web/js/lib'),
                    to: path.join(ROOT_PATH, 'dist/web')
                },
            ],
        }),
    ],
    output: {
        filename: '[name].[hash].js',
        chunkFilename: '[id].[hash].js',
        path: path.join(ROOT_PATH, 'dist/web')
    }
};
