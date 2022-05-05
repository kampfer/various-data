// 数据来源：知网-中国重要报纸全文数据库
// https://kns.cnki.net/kns/brief/result.aspx?dbprefix=CCND

import * as request from './request.js';

(async function () {
    const res = await request.post({
        url: 'https://kns.cnki.net/kns/request/SearchHandler.ashx',
        data: {
            action: '',
            NaviCode: '*',
            catalogName: 'ZJCLS',
            ua: 1.21,
            isinEn: 0,
            PageName: 'ASP.brief_result_aspx',
            DbPrefix: 'CCND',
            DbCatalog: '中国重要报纸全文数据库',
            ConfigFile: 'CCND.xml',
            db_opt: 'CCND',
            db_value: '中国重要报纸全文数据库综合',
            CKB_extension: 'ZYW',
            his: 0,
            __: new Date()
        }
    });
    const paramsString = res._body;
    const res2 = await request.get({
        url: 'https://kns.cnki.net/kns/brief/brief.aspx',
        data: {
            pagename: paramsString
        }
    });
    console.log(res2._body);
})();
