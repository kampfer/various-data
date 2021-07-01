// 回购定盘利率和银银间回购定盘利率

const request = require('./request');
const moment = require('moment');

module.exports = async function () {

    // 接口只能查最近一年的数据
    const endTime = moment();
    const startTime = moment().subtract(1, 'y').add(1, 'd');

    console.log({
        lang: 'CN',
        startDate: startTime.format('YYYY-MM-DD'),
        endDate: endTime.format('YYYY-MM-DD'),
        t: Date.now()
    });

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

    return {
        name: 'fr_fdr',
        description: '回购定盘利率和银银间回购定盘利率',
        source: 'http://www.chinamoney.com.cn/chinese/bkfrr/',
        data: json.records.map(({ frValueMap }) => frValueMap)
    };

}