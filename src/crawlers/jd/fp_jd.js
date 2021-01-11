const https = require('https');
const { URL } = require('url');
const querystring = require('querystring');

// https.get('https://sf.taobao.com/item_list.htm?category=50025969&city=%CE%E4%BA%BA', res => {

const params = {
    appid: 'paimai-search-soa',
    functionId: 'paimai_unifiedSearch',
    body: JSON.stringify({
        apiType: 2,
        page: 1,
        pageSize: 40,
        reqSource: 0,
        provinceId: '17'
    }),
    loginType: 3,
    jsonp: `jQuery${Date.now()}`,
    _: Date.now()
};
const jdApi = new URL('/api', 'https://api.m.jd.com/');
jdApi.search = querystring.stringify(params);
console.log(jdApi.toString());

https.get(jdApi.toString(), res => {
    res.setEncoding('utf8');
    let rawData = '';
    res.on('data', (chunk) => { rawData += chunk; });
    res.on('end', () => {
        try {
            // const parsedData = JSON.parse(rawData);
            console.log(rawData);
        } catch (e) {
            console.error(e.message);
        }
    });
});
