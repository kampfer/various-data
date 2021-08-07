import * as request from './request.js';

export default async function () {

    const res = await request.get({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bk-fx/RmbIdxChrt',
        data: {
            indexType: 3,
            t: Date.now()
        }
    });

    const { records } = res.json();

    // 从远到近排序

    return {
        name: 'rmbCFETSIndex',
        description: 'CFETS人民币汇率指数',
        source: 'http://www.chinamoney.com.cn/chinese/bkrmbidx/',
        data: records.map(d => ({
            date: d.showDateCn,
            indexRate: d.indexRate
        }))
    };

}
