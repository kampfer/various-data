const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

async function querySelectorAll(parent, selector) {
    const nodeList = await parent.findElement(By.css(selector)).catch(() => null);
    return nodeList;
}

(async function () {

    const options = new chrome.Options();
    options.addArguments('--ignore-certificate-errors');

    const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();

    await driver.get('https://data.stats.gov.cn/easyquery.htm?cn=A01');

    const table = await querySelectorAll(driver, '.table_container_main table');
    const text = await table.getText();
    console.log(text);

    await driver.quit();

})()