module.exports = {
    jobName: 'test',
    jobType: 'every',
    time: '10 seconds',
    handler(job, done) {
        console.log('test', (new Date()).toLocaleString());
        done(); // 必须调用done，否则断掉重启之后会卡住
    }
};