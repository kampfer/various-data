const fs = require('fs');
const path = require('path');
const { DATA_STORE_PATH } = require('../constants');
const ticketPutAndBackStatByMonth = require('../crawlers/ticketPutAndBackStatByMonth');

module.exports = {
    jobName: 'ticketPutAndBackStatByMonth',
    // https://github.com/agenda/agenda#creating-jobs
    jobType: 'now',   // every, schedule, now, create
    time: '10 seconds',
    handler(job, done) {
        ticketPutAndBackStatByMonth().then(({ data }) => {
            const list = data.resultList;
            let prev = 0;
            for(let i = list.length - 1; i >= 0; i--) {
                const cur = list[i];
                prev += Number(cur.netPutIn);
                cur.accPutIn = prev;
            }

            fs.writeFileSync(
                path.join(DATA_STORE_PATH, 'ticketPutAndBackStatByMonth.json'),
                JSON.stringify(list)
            );

            done();
        });
    }
};