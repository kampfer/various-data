const http = require('http');
const querystring = require('querystring');
const url = require('url');

exports.get = function(options) {
    const target = url.parse(options.url);

    return new Promise((resolve, reject) => {
        http.get({
            hostname: target.host,
            // port: 80,
            path: `${target.path}?${querystring.stringify(options.data)}`
        }, (res) => {
            res.setEncoding('utf8');
            let rawData = '';
            res.on('data', chunk => rawData += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(rawData));
                } catch (e) {
                    reject(e);
                }
            });
        });
    });
};

exports.post = function(options) {
    const target = url.parse(options.url);
    const postData = querystring.stringify(options.data);

    return new Promise((resolve, reject) => {
        const req = http.request({
            hostname: target.host,
            // port: 80,
            path: target.path,
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData)
            }
        }, res => {
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
};