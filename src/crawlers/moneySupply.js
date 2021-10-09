import moment from 'moment';
import * as request from './request.js';

function getPage(i) {
    return request.get({
        url: 'http://datainterface.eastmoney.com/EM_DataCenter/JS.aspx',
        data: {
            type: 'GJZB',
            sty: 'ZGZB',
            p: i,
            ps: 20,
            mkt: 11,
            pageNo: i,
            pageNum: i,
            js: '{"data":[(x)], "pages": (pc)}'
        }
    });
}

// http://data.eastmoney.com/cjsj/hbgyl.html
// 月份 M2数量 M2同比增长 M2环比增长 M1数量 M1同比增长 M1环比增长 M0数量 M0同比增长 M0环比增长
export default async function moneySupply() {
    let json = {
        name: 'moneySupply',
        description: '货币供应',
        source: 'http://data.eastmoney.com/cjsj/hbgyl.html',
        data: []
    };
    let total = 1;
    let cur = 0;
    while(++cur <= total) {
        const res = await getPage(cur);
        const { data: page, pages } = res.json();
        page.forEach(d => {
            const [date, m2, m2YOY, m2MOM, m1, m1YOY, m1MOM, m0, m0YOY, m0MOM] = d.split(',');
            json.data.unshift({
                date: moment(date, 'YYYY-MM-DD').valueOf(),
                displayDate: date,
                m2: Number(m2),
                m2YOY: Number(m2YOY),
                m2MOM: Number(m2MOM),
                m1: Number(m1),
                m1YOY: Number(m1YOY),
                m1MOM: Number(m1MOM),
                m0: Number(m0),
                m0YOY: Number(m0YOY),
                m0MOM: Number(m0MOM),
            });
        });
        total = pages;
    }
    return json.data;
}
