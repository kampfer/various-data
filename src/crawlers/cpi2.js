import * as request from './request.js';
import moment from 'moment';

function makeItem(d) {
    return {
        cpi: d.data.hasdata ? d.data.data : null,
        displayDate: d.wds[1].valuecode,
        date: moment(d.wds[1].valuecode, 'YYYY').endOf('year').valueOf()
    };
}

// 居民消费价格指数(上年=100)
export default async function cpi2() {

    // https://stackoverflow.com/questions/31673587/error-unable-to-verify-the-first-certificate-in-nodejs
    const NODE_TLS_REJECT_UNAUTHORIZED = process.env['NODE_TLS_REJECT_UNAUTHORIZED'];
    process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = 0;

    const res = await request.get({
        url: 'https://data.stats.gov.cn/easyquery.htm',
        data: {
            m: 'QueryData',
            dbcode: 'hgnd',
            rowcode: 'zb',
            colcode: 'sj',
            wds: `[]`,
            dfwds: JSON.stringify([{
                wdcode: 'zb',
                valuecode: 'A090101'
            }, {
                wdcode: 'sj',
                valuecode: '2010-'
            }]),
        }
    });

    const json = res.json();

    process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = NODE_TLS_REJECT_UNAUTHORIZED;

    return json.returndata.datanodes.map(d => makeItem(d));

}

cpi2();
