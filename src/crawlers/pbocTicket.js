const http = require('http');
const querystring = require('querystring');
const jsonexport = require('jsonexport');
const fs = require('fs');
const { DATA_STORE_PATH } = require('./constants');
const path = require('path');

function post(path, data) {
    const postData = querystring.stringify(data);
    const options = {
        hostname: 'www.chinamoney.com.cn',
        port: 80,
        path,
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-Length': Buffer.byteLength(postData)
        }
    }
    return new Promise((resolve, reject) => {
        const req = http.request(options, res => {
            res.setEncoding('utf8');
            let rawData = '';
            res.on('data', chunk => rawData += chunk);
            res.on('end', () => {
                try {
                    const parsedData = JSON.parse(rawData);
                    resolve(parsedData);
                } catch (e) {
                    reject(e);
                }
            });
        });
        req.on('error', e => reject(e));  
        // write data to request body
        req.write(postData);
        req.end();
    });
}

post('/ags/ms/cm-u-bond-publish/TicketPutAndBackMonthRegion').then(d => {
    const { maxMonth, maxMonthYear, minMonth, minMonthYear } = d.data.ticketPutAndBackMonthRegion;
    const months = (maxMonthYear - minMonthYear) * 12 + (maxMonth - minMonth) + 1;
    console.log(months);
    return post('/ags/ms/cm-u-bond-publish/TicketPutAndBackStatByMonth', {
        startMonth: `${minMonthYear}-${minMonth}`,
        endMonth: `${maxMonthYear}-${maxMonth}`,
        pageSize: months,
        pageNo: 1,
    }).then(d => {
        // jsonexport(d.data.resultList, function(err, csv) {
        //     if (err) return console.error(err);
        //     fs.writeFileSync(`./${Date.now()}.csv`, csv);
        // });
        fs.writeFileSync(
            path.join(DATA_STORE_PATH, 'pbocTicket.json'),
            JSON.stringify(d.data.resultList)
        );

        // const values = [];
        // let prev = 0;
        // for(let i = d.data.resultList.length - 1; i >= 0; i--) {
        //     const cur = d.data.resultList[i];
        //     prev += Number(cur.netPutIn);
        //     values.push({ value: prev, date: cur.date });
        // }
        // jsonexport(values, function(err, csv) {
        //     if (err) return console.error(err);
        //     fs.writeFileSync(`./${Date.now()}.csv`, csv);
        // });
    }, e => console.log(e));
}, e => console.log(e));
