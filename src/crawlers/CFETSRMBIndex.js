import moment from 'moment';
import * as request from './request.js';

export default async function () {

    const res = await request.get({
        url: 'https://www.chinamoney.com.cn/ags/ms/cm-u-bk-fx/RmbIdxChrt',
        data: {
            indexType: 3,
            t: Date.now()
        }
    });

    const { records } = res.json();

    // 从远到近排序

    return records.reverse().map(d => ({
        date: moment(d.showDateCn, 'YYYY-MM-DD').valueOf(),
        displayDate: d.showDateCn,
        indexRate: d.indexRate
    }));

}
