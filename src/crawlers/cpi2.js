const request = require('./request');

// https://stackoverflow.com/questions/31673587/error-unable-to-verify-the-first-certificate-in-nodejs
process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = 0;

request.post({
    url: 'https://data.stats.gov.cn/easyquery.htm',
    data: {
        id: 'zb',
        dbcode: 'hgyd',
        wdcode: 'zb',
        m: 'getTree'
    }
}).then(res => console.log(res));
