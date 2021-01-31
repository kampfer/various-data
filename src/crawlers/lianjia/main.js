const { Builder, By, Key, until } = require('selenium-webdriver');
const fs = require('fs');
const jsonexport = require('jsonexport');

// https://www.selenium.dev/selenium/docs/api/javascript/index.html
// https://www.selenium.dev/documentation/en/webdriver/driver_requirements/

async function extractPageInfo(href, driver) {
    await driver.get(href);
    const liList = await driver.findElements(By.css('.listContent > li'));
    const infoList = await Promise.all(
        liList.map(li => extractElemInfo(li, driver))
    );
    return infoList;
};

async function findNextPage(driver) {
    const elem = await driver.findElement(By.css('.house-lst-page-box > a.on + a')).catch(() => null);
    if (elem) {
        return elem.getAttribute('href');
    } else {
        return null;
    }
}

async function extractElemInfo(element, driver) {
    const a = await element.findElement(By.css('.title > a'));
    const title = await a.getText();
    const href = await a.getAttribute('href');

    const dealDateElem = await element.findElement(By.css('.dealDate')).catch(() => null);
    const dealDate = await (dealDateElem ? dealDateElem.getText() : null);

    const totalPriceElem = await element.findElement(By.css('.totalPrice')).catch(() => null);
    const totalPrice = await (totalPriceElem ? totalPriceElem.getText() : null);

    const positionInfoElem = await element.findElement(By.css('.positionInfo')).catch(() => null);
    const positionInfo = await (positionInfoElem ? positionInfoElem.getText() : null);

    const unitPriceElem = await element.findElement(By.css('.unitPrice')).catch(() => null);
    const unitPrice = await (unitPriceElem ? unitPriceElem.getText() : null);

    const dealHouseTxtElem = await element.findElement(By.css('.dealHouseTxt')).catch(() => null);
    const dealHouseTxt = await (dealHouseTxtElem ? dealHouseTxtElem.getText() : null);

    return {
        title,
        href,
        dealDate,
        totalPrice,
        positionInfo,
        unitPrice,
        dealHouseTxt
    };
}

async function extract(url, driver) {
    const data = [];
    try {
        let nextPage = url;
        if (!nextPage) {
            return console.log('url未指定')
        }
        let page = 0;
        while(nextPage) {
            const info = await extractPageInfo(nextPage, driver);
            data.push(...info);
            console.log(`${nextPage}/第${++page}页/+${info.length}/总数: ${data.length}`);
            nextPage = await findNextPage(driver);
        }
    } catch (e) {
        console.log(e);
    } finally {
        fs.writeFileSync(`./${Date.now()}.json`, JSON.stringify(data, null, '\t'));
        jsonexport(data, function(err, csv) {
            if (err) return console.error(err);
            fs.writeFileSync(`./${Date.now()}.csv`, csv);
        });
        await driver.quit();
    }
}

// 万科魅力之城 https://wh.lianjia.com/chengjiao/c3711060258233/
// 当代国际城   https://wh.lianjia.com/chengjiao/c3711063315968/
(async function main() {
    const driver = await new Builder().forBrowser('chrome').build();
    const args = process.argv.slice(2);
    extract(args[0] || 'https://wh.lianjia.com/chengjiao/c3711060258233/', driver)
})();