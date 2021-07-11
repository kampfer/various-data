// 回购定盘利率和银银间回购定盘利率

const request = require('./request');
const moment = require('moment');
const { DATA_STORE_PATH } = require('../constants');
const fs = require('fs');
const path = require('path');

module.exports = async function () {

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
    const { data } = JSON.parse(
        fs.readFileSync(path.join(DATA_STORE_PATH, 'fr_fdr.json'))
    );
    const lastest = moment(data[0].date);
    const { records: newData } = json;
    for(let i = newData.length - 1; i >= 0; i--) {
        const d = newData[i].frValueMap;
        if (moment(d.date).isAfter(lastest)) {
            data.unshift(d);
        }
    }

    return {
        name: 'fr_fdr',
        description: '回购定盘利率和银银间回购定盘利率',
        source: 'http://www.chinamoney.com.cn/chinese/bkfrr/',
        data,
    };

}