import chrome from 'selenium-webdriver/chrome.js';
import {Builder, By, promise} from 'selenium-webdriver';
import { DRIVER_PATH, DATA_STORE_PATH } from '../constants/path.js';
import moment from 'moment';
import fs from 'fs';
import path from 'path';

// https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/historyQuery?startDate=2021-01-01&endDate=2021-10-09&gjqx=0&qxId=hzsylqx&locale=cn_ZH&mark=1
function makeUrl(data) {
    let startDate;
    if (data && data.length > 0) {
        startDate = moment(data[data.length - 1]).add(1, 'days').format('YYYY-MM-DD');
    } else {
        startDate = moment(`${moment().year()}-01-01`, 'YYYY-MM-DD').format('YYYY-MM-DD');
    }

    const endDate = moment().format('YYYY-MM-DD');

    return `https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/historyQuery?startDate=${startDate}&endDate=${endDate}&gjqx=0&qxId=hzsylqx&locale=cn_ZH&mark=1`;

}

export default async function nationalDebt(indicator) {
    chrome.setDefaultService(new chrome.ServiceBuilder(DRIVER_PATH).build());
    const opts = new chrome.Options();
    const driver = await new Builder()
        .forBrowser('chrome')
        .setChromeOptions(opts.headless())
        .build();

    let data;
    try {
        let json = JSON.parse(
            fs.readFileSync(path.join(DATA_STORE_PATH, indicator.dataPath))
        );
        data = json.data;
    } catch(e) {
        console.log(e);
        data = [];
    }
    const url = makeUrl(data);

    await driver.get(url);
    const table = await driver.findElement(By.css('#gjqxData table'));
    const date = await table.findElements(By.css('tr td:nth-child(2)'));
    const quarterYear = await table.findElements(By.css('tr td:nth-child(3)'));
    const halfYear = await table.findElements(By.css('tr td:nth-child(4)'));
    const oneYear = await table.findElements(By.css('tr td:nth-child(5)'));
    const threeYear = await table.findElements(By.css('tr td:nth-child(6)'));
    const fiveYear = await table.findElements(By.css('tr td:nth-child(7)'));
    const sevenYear = await table.findElements(By.css('tr td:nth-child(8)'));
    const tenYear = await table.findElements(By.css('tr td:nth-child(9)'));
    const thirtyYear = await table.findElements(By.css('tr td:nth-child(10)'));

    for(let i = 1, l = date.length; i < l; i++) {
        const values = await Promise.all([
            date[i].getText(),
            quarterYear[i].getText(),
            halfYear[i].getText(),
            oneYear[i].getText(),
            threeYear[i].getText(),
            fiveYear[i].getText(),
            sevenYear[i].getText(),
            tenYear[i].getText(),
            thirtyYear[i].getText(),
        ]);
        data.push({
            date: moment(values[0], 'YYYY-MM-DD').valueOf(),
            quarterYear: parseFloat(values[1], 10),
            halfYear: parseFloat(values[2], 10),
            oneYear: parseFloat(values[3], 10),
            threeYear: parseFloat(values[4], 10),
            fiveYear: parseFloat(values[5], 10),
            sevenYear: parseFloat(values[6], 10),
            tenYear: parseFloat(values[7], 10),
            thirtyYear: parseFloat(values[8], 10),
        });
    }

    await driver.quit();

    return data;
}
