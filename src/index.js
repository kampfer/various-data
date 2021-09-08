import express from 'express';
import path from 'path';
import fs from 'fs';
import * as crawlers from './crawlers/index.js';
import { ROOT_PATH, DATA_STORE_PATH } from './constants.js';
import bodyParser from 'body-parser';    //解析,用req.body获取post参数

const app = express();
app.use(bodyParser.json());
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

app.get('/api/getIndicatorList', async (req, res) => {
    const data = fs.readFileSync(path.join(DATA_STORE_PATH, 'indicatorList.json'));
    res.json({
        code: 200,
        data: JSON.parse(data)
    });
});

app.post('/api/addIndicator', async(req, res) => {
    const jsonPath = path.join(DATA_STORE_PATH, 'indicatorList.json');
    const data = JSON.parse(fs.readFileSync(jsonPath));
    const newData = { ...req.body, type: 0 };   // type: 0 手动添加的指标
    const exited = !!data.find(d => d.name === newData.name);
    if (exited) {
        res.json({ code: 201, msg: `${newData.name}已存在` });
    } else {
        data.push(newData);
        fs.writeFileSync(jsonPath, JSON.stringify(data, null, 4));
        res.json({ code: 200, data: newData });
    }
});

app.listen(3000);

console.log(`listening 3000`);