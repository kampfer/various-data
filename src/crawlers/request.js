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

exports.post = function() {};