module.exports = {
    jobName: 'ticketPutAndBackStatByMonth',
    // https://github.com/agenda/agenda#creating-jobs
    jobType: 'every',   // every, schedule, now, create
    time: '10 seconds',
    handler(job, done) {
        console.log('ticketPutAndBackStatByMonth', (new Date()).toLocaleString());
        done();
    }
};