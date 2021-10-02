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
    const indicatorData = JSON.parse(fs.readFileSync(path.join(DATA_STORE_PATH, `${id}.json`)));
    const fieldList = indicatorData.fieldList;
    const newRow = {};
    fieldList.forEach(name => newRow[name] = row[name]);
    const index = indicatorData.data.findIndex(d => d.date === newRow.date);
    if (index > -1) {   // 存在date相同的数据，提示错误
        res.json({ code: 201, msg: `${moment(newRow.date).format('YYYY-MM-DD')}已存在！` });
    } else {
        indicatorData.data.push(newRow);
        indicatorData.updateTime = Date.now();
        fs.writeFileSync(indicatorData.dataPath, JSON.stringify(indicatorData, null, 4));
        res.json({ code: 200, data: newRow });
    }
});

// TODO addIndicatorRow和saveIndicatorRow逻辑类似，可以考虑提取共用逻辑
app.post('/api/updateIndicatorRow', (req, res) => {
    const id = req.body.id;
    const row = req.body.row;
    const indicatorData = JSON.parse(fs.readFileSync(path.join(DATA_STORE_PATH, `${id}.json`)));
    const fieldList = indicatorData.fieldList;
    const newRow = {};
    fieldList.forEach(name => newRow[name] = row[name]);
    const index = indicatorData.data.findIndex(d => d.date === newRow.date);
    if (index > -1) {
        const row = indicatorData.data[index];
        indicatorData.data.splice(index, 1, { ...row, ...newRow });
        fs.writeFileSync(indicatorData.dataPath, JSON.stringify(indicatorData, null, 4));
        res.json({ code: 200, data: newRow });
    } else {
        // indicatorData.data.push(newRow);
        // indicatorData.updateTime = Date.now();
        // fs.writeFileSync(indicatorData.dataPath, JSON.stringify(indicatorData, null, 4));
        // res.json({ code: 200, data: newRow });
        res.json({ code: 201, msg: `${moment(newRow.date).format('YYYY-MM-DD')}不存在！` });
    }
});

app.get('/api/deleteIndicatorRow', (req, res) => {
    const id = req.query.id;
    const date = parseFloat(req.query.date, 10);
    const indicatorData = JSON.parse(fs.readFileSync(path.join(DATA_STORE_PATH, `${id}.json`)));
    const index = indicatorData.data.findIndex(d => d.date === date);
    if (index > -1) {
        indicatorData.data.splice(index, 1);
        fs.writeFileSync(indicatorData.dataPath, JSON.stringify(indicatorData, null, 4));
    }
    res.json({ code: 200 });
});

app.listen(3000);

console.log(`listening 3000`);