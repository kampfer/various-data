// 回购定盘利率和银银间回购定盘利率

import * as request from './request.js';
import moment from 'moment';
import  { DATA_STORE_PATH } from '../constants.js';
import fs from 'fs';
import path from 'path';

export default async function (indicator) {

    // 接口只能查最近一年的数据
    const endTime = moment();
    const startTime = moment().subtract(1, 'y').add(1, 'd');

    const res = await request.get({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/FrrHis',
        data: {
            lang: 'CN',
            startDate: startTime.format('YYYY-MM-DD'),
            endDate: endTime.format('YYYY-MM-DD'),
            t: Date.now()
        }
    });

    const json = res.json();
    const data = JSON.parse(
        fs.readFileSync(path.join(DATA_STORE_PATH, `${indicator.id}.json`))
    );
    const lastest = moment(data[data.length - 1].date);
    const { records: newData } = json;
    for(let i = newData.length - 1; i >= 0; i--) {
        const d = newData[i].frValueMap;
        const now = moment(d.date);
        if (now.isAfter(lastest)) {
            d.displayDate = d.date;
            d.date = now.valueOf();
            data.push(d);
        }
    }

    return data;

}