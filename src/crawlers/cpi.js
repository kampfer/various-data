const request = require('./request');

// https://stackoverflow.com/questions/31673587/error-unable-to-verify-the-first-certificate-in-nodejs
process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = 0;

module.exports = async function cpi() {
    const data = await request.get({
        url: 'https://data.stats.gov.cn/easyquery.htm',
        data: {
            m: 'QueryData',
            dbcode: 'hgyd',
            rowcode: 'zb',
            colcode: 'sj',
            wds: `[]`,
            dfwds: `[{"wdcode":"sj","valuecode":"last100"}]`,
        }
    });
    return data;
}