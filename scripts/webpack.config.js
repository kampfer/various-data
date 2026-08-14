// 参考配置：
// https://raw.githubusercontent.com/kampfer/gltf2-viewer/master/scripts/webpack.config.js

import { CleanWebpackPlugin } from 'clean-webpack-plugin';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_PATH = path.resolve(__dirname, '..');

export default {
    entry: path.join(ROOT_PATH, 'src/web/frontEnd/src/main.js'),
    resolve: {
        // 默认值为 ['.js', '.json', '.wasm']，必须显式加入 TS 扩展名，
        // 否则新 TS 文件的无扩展名 import 无法解析
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
        alias: {
            // 与 tsconfig.json 的 paths 对应（可选）
            '@ledger': path.join(ROOT_PATH, 'src/web/frontEnd/src'),
        },
    },
    module: {
        rules: [
            {
                // 同时覆盖既有 .js / .jsx 与新增 .ts / .tsx
                test: /\.[jt]sx?$/,
                // package.json 使用 type=module；允许设计约定的无扩展名 TS 目录入口（如 './store'）
                resolve: {
                    fullySpecified: false,
                },
                exclude: /(node_modules|bower_components)/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        // @babel/preset-typescript 内部按文件扩展名启用，
                        // 对既有 .js 文件不产生任何行为变化
                        presets: ['@babel/preset-react', '@babel/preset-typescript']
                    }
                }
            },
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    "style-loader",
                    {
                        loader: 'css-loader',
                        options: {
                            modules: {
                                // https://webpack.js.org/loaders/css-loader/#auto
                                auto: true,
                            //     mode: 'local',
                                localIdentName: '[local]__[hash]'
                            }
                        }
                    },
                    "sass-loader",
                ],
            },
        ]
    },
    plugins: [
        new CleanWebpackPlugin(),
        new HtmlWebpackPlugin({
            filename: 'index.html',
            template: path.join(ROOT_PATH, 'src/web/frontEnd/src/index.html'),
            inject: 'body'
        })
    ],
    output: {
        filename: '[name].[fullhash].js',
        chunkFilename: '[id].[fullhash].js',
        path: path.join(ROOT_PATH, 'dist/web')
    }
};
