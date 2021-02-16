const fs = require('fs');
const path = require('path');
const { DATA_STORE_PATH } = require('../constants');
const cpi = require('../crawlers/cpi');

module.exports = {
    jobName: 'cpi',
    jobType: 'every',
    time: '1 week',
    handler(job, done) {
        cpi().then((data) => {
            fs.writeFileSync(
                path.join(DATA_STORE_PATH, 'cpi.json'),
                JSON.stringify(data)
            );
            done();
        });
    }
};