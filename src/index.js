import express from 'express';
import path from 'path';
import fs from 'fs';
import * as crawlers from './crawlers/index.js';
import { ROOT_PATH, DATA_STORE_PATH } from './constants.js';
import bodyParser from 'body-parser';    //解析,用req.body获取post参数
import { v4 as uuidv4 } from 'uuid';
import {
    MANUAL_UPDATE_INDICATOR
}  from './constants/indicatorTypes.js';
import moment from 'moment';

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
    const indicatorFiles = fs.readdirSync(DATA_STORE_PATH)
        .filter(fileName => path.extname(fileName) === '.json')
        .map(fileName => path.join(DATA_STORE_PATH, fileName));
    const data = indicatorFiles.map(filePath => {
            const indicatorData = JSON.parse(fs.readFileSync(filePath));
            if (!indicatorData.id) indicatorData.id = indicatorData.name;   // 旧数据没有id，用name代替
            if (!indicatorData.fieldList) indicatorData.fieldList = Object.keys(indicatorData.data[0]);
            delete indicatorData.data;  // 这个接口不需要data，而且data可能很大，所以删除掉
            return indicatorData;
        })
        .sort((a, b) => {
            if (a.createTime && b.createTime) {
                return a.createTime - b.createTime;
            } else if (!a.createTime) {
                return -1;
            } else if (!b.createTime) {
                return 1;
            } else {
                return 0;
            }
        });
    res.json({code: 200, data });
});

app.post('/api/addIndicator', async(req, res) => {
    const indicatorId = uuidv4();
    const now = Date.now();
    const newIndicator = {
        ...req.body,
        fieldList: ['date', ...req.body.fieldList.split(',')],
        id: indicatorId,
        data: [],
        dataPath: path.join(DATA_STORE_PATH, `${indicatorId}.json`),    // 注意不允许保存在DATA_STORE_PATH的子目录中!
        type: MANUAL_UPDATE_INDICATOR,
        createTime: now,
        updateTime: now,
    };

    const indicatorIdList = fs.readdirSync(DATA_STORE_PATH)
        .filter(fileName => path.extname(fileName) === '.json')
        .map(fileName => path.basename(fileName, '.json'));
    const exited = indicatorIdList.find(id => id === newIndicator.id);

    if (exited) {
        res.json({ code: 201, msg: `${newIndicator.name}已存在` });
    } else {
        // 创建数据存储文件
        fs.writeFileSync(newIndicator.dataPath, JSON.stringify(newIndicator, null, 4));
        // fs.writeFileSync(newIndicator.dataPath, JSON.stringify(newIndicator));
        res.json({ code: 200, data: newIndicator });
    }
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

app.listen(3000);

console.log(`listening 3000`);