const fs = require('fs');
const path = require('path');
const { DATA_STORE_PATH } = require('../constants');
const moneySupply = require('../crawlers/moneySupply');

module.exports = {
    jobName: 'moneySupply',
    jobType: 'now', 
    handler(job, done) {
        moneySupply().then((data) => {
            fs.writeFileSync(
                path.join(DATA_STORE_PATH, 'moneySupply.json'),
                JSON.stringify(data)
            );
            done();
        });
    }
};