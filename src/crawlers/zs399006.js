import * as request from './request.js';
import moment from 'moment';
import  { DATA_STORE_PATH } from '../constants.js';
import path from 'path';

export default async function () {
    const res = await request.get({
        url: 'https://push2his.eastmoney.com/api/qt/stock/kline/get',
        data: {
            secid: '0.399006',
            fields1: 'f1,f2,f3,f4,f5',
            fields2: 'f51,f52,f53,f54,f55,f56,f57,f58',
            beg: '19900101',
            end: '20220101',
            klt: '101',
            fqt: '0'
        }
    });
    // open close top bottom
    return res.json().data.klines.map(s => {
        const parts = s.split(',');
        return {
            date: moment(parts[0], 'YYYY-MM-DD').valueOf(),
            open: parts[1],
            close: parts[2],
            top: parts[3],
            bottom: parts[4],
        };
    });
}