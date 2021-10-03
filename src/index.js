import express from 'express';
import path from 'path';
import fs from 'fs';
import { ROOT_PATH, DATA_STORE_PATH } from './constants.js';
import bodyParser from 'body-parser';    //解析,用req.body获取post参数
import moment from 'moment';
import IndicatorManager from './IndicatorManager.js';

const indicatorManager = new IndicatorManager({ storePath: DATA_STORE_PATH });

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.resolve(ROOT_PATH, 'dist/web')));
app.use('/data', express.static(DATA_STORE_PATH));

app.get('/api/crawlIndicator', async (req, res) => {
    const id = req.query.id;
    const indicator = indicatorManager.getIndicator(id);
    if (indicator) {
        console.log(`开始抓取${indicator.name}数据`);
        const data = await indicatorManager.crawlIndicator(id);
        console.log(`成功抓取${indicator.name}数据`);
        res.json({ code: 200, data });
    } else {
        res.json({ code: 202, msg: '爬虫不存在' });
    }
});

app.get('/api/getIndicatorList', async (req, res) => {
    const data = indicatorManager.getIndicatorList();
    res.json({code: 200, data });
});

app.post('/api/addIndicator', async(req, res) => {
    const newIndicator = indicatorManager.addIndicator(req.body);
    res.json({ code: 200, data: newIndicator });
});

app.get('/api/deleteIndicator', (req, res) => {
    const { id } = req.query;
    try {
        indicatorManager.deleteIndicator(id);
    } catch(e) {
        // noop
    }
    res.json({ code: 200 });
});

app.post('/api/addIndicatorRow', (req, res) => {
    const id = req.body.id;
    const row = req.body.row;
    const indicator = indicatorManager.getIndicator(id);
    const newRow = indicator.addRow(row);
    res.json({ code: 200, data: newRow });
});

// TODO addIndicatorRow和saveIndicatorRow逻辑类似，可以考虑提取共用逻辑
app.post('/api/updateIndicatorRow', (req, res) => {
    const id = req.body.id;
    const row = req.body.row;
    const indicator = indicatorManager.getIndicator(id);
    const newRow = indicator.updateRow(row);
    res.json({ code: 200, data: newRow });
});

app.get('/api/deleteIndicatorRow', (req, res) => {
    const id = req.query.id;
    const date = parseFloat(req.query.date, 10);
    const indicator = indicatorManager.getIndicator(id);
    indicator.deleteRow(date);
    res.json({ code: 200 });
});

app.listen(3000);

console.log(`listening 3000`);