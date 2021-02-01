// const http = require('http');
// const querystring = require('querystring');

const request = require('./request');

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

module.exports = async function moneySupply() {
    let data = [];
    let total = 1;
    let cur = 0;
    while(++cur <= total) {
        const res = await getPage(cur);
        const { data: page, pages } = res.json();
        data.push(...page);
        total = pages;
    }
    return data;
}
