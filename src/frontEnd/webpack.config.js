// 调度器后台管理的生产构建配置。
// 配置与源码同放 src/frontEnd，与旧 src/web/frontEnd、scripts/webpack.* 完全隔离。

import { CleanWebpackPlugin } from 'clean-webpack-plugin';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, 'src');

export default {
    entry: path.join(SRC_DIR, 'main.tsx'),
    resolve: {
        extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
    },
    module: {
        rules: [
            {
                test: /\.[jt]sx?$/,
                resolve: {
                    // package.json 使用 type=module，允许无扩展名的 TS 目录入口
                    fullySpecified: false,
                },
                exclude: /(node_modules|bower_components)/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ['@babel/preset-react', '@babel/preset-typescript'],
                    },
                },
            },
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
        ],
    },
    plugins: [
        // 只清理本应用的产物目录，不触碰 dist/web
        new CleanWebpackPlugin(),
        new HtmlWebpackPlugin({
            filename: 'index.html',
            template: path.join(__dirname, 'index.html'),
            inject: 'body',
        }),
    ],
    output: {
        filename: '[name].[fullhash].js',
        chunkFilename: '[id].[fullhash].js',
        path: path.join(__dirname, 'dist'),
    },
};
