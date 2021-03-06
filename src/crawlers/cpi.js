const request = require('./request');

function makeItem(d) {
    return {
        cpi: d.data.hasdata ? d.data.data : null,
        date: d.wds[1].valuecode
    };
}

async function cpi() {
    // https://stackoverflow.com/questions/31673587/error-unable-to-verify-the-first-certificate-in-nodejs
    const NODE_TLS_REJECT_UNAUTHORIZED = process.env['NODE_TLS_REJECT_UNAUTHORIZED'];
    process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = 0;

    // 2016- 上月100
    const res = await request.get({
        url: 'https://data.stats.gov.cn/easyquery.htm',
        data: {
            m: 'QueryData',
            dbcode: 'hgyd',
            rowcode: 'zb',
            colcode: 'sj',
            wds: `[]`,
            dfwds: JSON.stringify([{
                wdcode: 'zb',
                valuecode: 'A01030101'
            }, {
                wdcode: 'sj',
                valuecode: '2016-'
            }]),
        }
    });

    // 2001-2015 上月100
    const res2 = await request.get({
        url: 'https://data.stats.gov.cn/easyquery.htm',
        data: {
            m: 'QueryData',
            dbcode: 'hgyd',
            rowcode: 'zb',
            colcode: 'sj',
            wds: `[]`,
            dfwds: JSON.stringify([{
                wdcode: 'zb',
                valuecode: 'A01030201'
            }, {
                wdcode: 'sj',
                valuecode: '2001-2015'
            }]),
        }
    });

    process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = NODE_TLS_REJECT_UNAUTHORIZED;

    const json1 = res.json();
    const json2 = res2.json();

    return {
        name: 'cpi',
        description: '全国居民消费价格指数（上月=100）',
        source: 'https://data.stats.gov.cn/easyquery.htm',
        data: json1.returndata.datanodes.map(d => makeItem(d)).concat(
            json2.returndata.datanodes.map(d => makeItem(d))
        )
    };
}

module.exports = cpi;
