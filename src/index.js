import express from 'express';
import path from 'path';
import fs from 'fs';
import * as crawlers from './crawlers/index.js';
import { ROOT_PATH, DATA_STORE_PATH } from './constants.js';

const app = express();
app.use(express.static(path.resolve(ROOT_PATH, 'dist/web')));
app.use('/data', express.static(DATA_STORE_PATH));

app.get('/api/update', async (req, res) => {
    const name = req.query.name;
    const crawler = crawlers[name];
    if (crawler) {
        console.log(`开始抓取${name}数据`);
        const data = await crawler();
        console.log(`成功抓取${name}数据`);
        fs.writeFileSync(
            path.join(DATA_STORE_PATH, `${name}.json`),
            JSON.stringify(data)
        );
        res.json({
            code: 200
        });
    }
});
 
app.listen(3000);

console.log(`listening 3000`);