import {Builder, By} from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';
import path from 'path';
import { ROOT_PATH } from '../constants.js';
import moment from 'moment';

const sources = [
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2021/07/2021071516002091976.htm',  // 2021
        rows: [4, 29],
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2021/01/2021011817520862940.htm',   // 2020
        rows: [4, 29]
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2020/01/2020011716363947588.htm',   // 2019
        rows: [4, 29]
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2019/01/2019011618592270314.htm',   // 2018
        rows: [4, 27]
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2018/01/2018011515315872258.htm',   // 2017
        rows: [4, 27]
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2017/01/2017011616170598114.htm',   // 2016
        rows: [4, 26]
    },
    {
        url: 'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2016/01/2016011510420280670.htm',   // 2015
        rows: [4, 26]
    },
    {
        url: 'http://www.pbc.gov.cn/eportal/fileDir/defaultCurSite/resource/cms/2015/07/2014s04.htm',    // 2014
        rows: [4, 26]
    },
    {
        url: 'http://www.pbc.gov.cn/eportal/fileDir/defaultCurSite/resource/cms/2015/07/2013s04.htm',    // 2013
        rows: [4, 26]
    },
];

export default async function balanceSheetofMonetaryAuthority() {
    chrome.setDefaultService(new chrome.ServiceBuilder(path.join(ROOT_PATH, 'bin/chromedriver.exe')).build());
    const opts = new chrome.Options();
    const driver = await new Builder()
        .forBrowser('chrome')
        .setChromeOptions(opts.headless())
        .build();
    let data = [];
    for(let { url, rows } of sources) {
        await driver.get(url);
        const body = await driver.findElement(By.css('table'));
        const content = await body.getText();
        // console.log(content.split('\n').slice(...rows));
        const regx = /^([\u4e00-\u9fa5\s：]+)([A-Za-z\s-: ]+)([\d.\s]+)/;
        const yearData = [];
        content.split('\n').slice(...rows).map((str, i) => {
            // console.log(str.match(regx));
            const matches = str.match(regx);
            if (i === 0) {
                // 日期
                matches[3].trim()
                    .split(/\s+/)
                    .forEach(d => yearData.push({
                        date: moment(d, 'YYYY.MM').valueOf(),
                        displayDate: d,
                    }));
            } else {
                const key = matches[2].replace(/[^a-zA-Z]+/g, '');
                matches[3].trim().split(/\s+/).forEach((d, i) => {
                    yearData[i][key] = parseFloat(d, 10);
                });
            }
        });
        data = [...yearData.filter(d => Object.keys(d).length > 1), ...data];
    }
    // console.log(data);
    await driver.quit();
    return data;
}
