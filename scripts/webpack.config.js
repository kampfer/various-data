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
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /(node_modules|bower_components)/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ['@babel/preset-react']
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
