import {Builder, By} from 'selenium-webdriver';
import chrome from 'selenium-webdriver/chrome.js';
import path from 'path';
import { ROOT_PATH } from '../constants.js';

const sources = [
    'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2021/07/2021071516002091976.htm',
    'http://www.pbc.gov.cn/diaochatongjisi/resource/cms/2021/01/2021011817520862940.htm',
];

export default async function balanceSheetofMonetaryAuthority() {
    chrome.setDefaultService(new chrome.ServiceBuilder(path.join(ROOT_PATH, 'bin/chromedriver.exe')).build());
    const opts = new chrome.Options();
    const driver = await new Builder()
        .forBrowser('chrome')
        .setChromeOptions(opts.headless())
        .build();
    let data = [];
    for(let source of sources) {
        await driver.get(source);
        const body = await driver.findElement(By.css('table'));
        const content = await body.getText();
        // console.log(content.split('\n').slice(4, 29));
        const regx = /^([\u4e00-\u9fa5\s：]+)([A-Za-z\s-: ]+)([\d.\s]+)/;
        const yearData = [];
        content.split('\n').slice(4, -4).map((str, i) => {
            // console.log(str.match(regx));
            const matches = str.match(regx);
            if (i === 0) {
                // 日期
                matches[3].split(' ').forEach(d => yearData.push({ date: d}));
            } else {
                const key = matches[2].replace(/[^a-zA-Z]+/g, '');
                matches[3].split(' ').forEach((d, i) => {
                    yearData[i][key] = parseFloat(d, 10);
                });
            }
        });
        data = [...yearData, data];
    }
    // console.log(data);
    await driver.quit();
    return {
        name: 'Balance Sheet of Monetary Authority',
        description: '货币当局资产负债表',
        source: 'http://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html',
        data
    };
}
