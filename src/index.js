const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();

app.use(express.static(path.join(__dirname, 'web')));
app.use('/data', express.static(path.join(__dirname, '../data')));

const crawlers = {
    cpi: './crawlers/cpi.js',
    moneySupply: './crawlers/moneySupply.js',
    ticketPutAndBackStatByMonth: './crawlers/ticketPutAndBackStatByMonth.js',
};

const { DATA_STORE_PATH } = require('./constants');

app.get('/api/update', async (req, res) => {
    const name = req.query.name;
    const { default: crawler } = await import(crawlers[name]);
    const data = await crawler();
    fs.writeFileSync(
        path.join(DATA_STORE_PATH, `${name}.json`),
        JSON.stringify(data)
    );
    res.json({
        code: 200
    });
});
 
app.listen(3000);