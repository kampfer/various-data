const http = require('http');
const https = require('https');
const querystring = require('querystring');
const { URL } = require('url');

class Res {

    constructor(res, body) {
        this._res = res;
        this._body = body;
    }

    json() {
        return JSON.parse(this._body);
    }

    cookies() {
        return this._res.headers['set-cookie'];
    }

}

function fetch({
    url,
    method,
    headers,
    data,
}) {
    return new Promise((resolve, reject) => {
        const isPost = method.toLowerCase() === 'post';
        const requestData = querystring.stringify(data);

        const target = new URL(url);
        const urlOptions = {
            protocol: target.protocol,
            hostname: target.hostname,
            port: target.port,
            path: `${target.pathname}${isPost ? target.search : `?${target.search.substr(1)}&${requestData}`}`, // Should include query string if any
        };

        const headersOptions = { ...headers };
        if (isPost) {
            Object.assign(headersOptions, {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(requestData)
            });
        }

        const requestOptions = {
            ...urlOptions,
            headers: headersOptions,
            method,
        };

        const req = (target.protocol === 'https:' ? https : http)
            .request(requestOptions, res => {
                res.setEncoding('utf8');
                let rawData = '';
                res.on('data', chunk => rawData += chunk);
                res.on('end', () => {
                    try {
                        // const parsedData = JSON.parse(rawData);
                        resolve(new Res(res, rawData));
                    } catch (e) {
                        reject(e);
                    }
                });
            });
        req.on('error', e => reject(e));
        // write data to request body
        req.write(requestData);
        req.end();
    });
}

exports.get = function(options) {
    options.method = 'GET';
    return fetch(options);
};

exports.post = function(options) {
    options.method = 'POST';
    return fetch(options);
};
