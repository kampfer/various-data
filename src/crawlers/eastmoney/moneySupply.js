const http = require('http');
const querystring = require('querystring');
// const jsonexport = require('jsonexport');
const fs = require('fs');
const { DATA_STORE_PATH } = require('../constants');
const path = require('path');


function get(data) {
    const search = querystring.stringify(data);

    return new Promise((resolve, reject) => {
        http.get({
            hostname: 'datainterface.eastmoney.com',
            port: 80,
            path: `/EM_DataCenter/JS.aspx?${search}`
        }, (res) => {
            res.setEncoding('utf8');
            let rawData = '';
            res.on('data', chunk => rawData += chunk);
            res.on('end', () => {
                try {
                    resolve(rawData);
                } catch (e) {
                    reject(e);
                }
            });
        });
    });
}

function getPage(i) {
    return get({
        type: 'GJZB',
        sty: 'ZGZB',
        p: i,
        ps: 20,
        mkt: 11,
        pageNo: i,
        pageNum: i,
        js: '{"data":[(x)], "pages": (pc)}'
    }).then(data => JSON.parse(data));
}

async function main() {
    let data = [];
    let total = 1;
    let cur = 0;
    while(++cur <= total) {
        await getPage(cur).then(json => {
            data.push(...json.data);
            total = json.pages;
            return json;
        });
    }
    fs.writeFileSync(
        path.join(DATA_STORE_PATH, 'moneySupply.json'),
        JSON.stringify(data)
    );
}

main();