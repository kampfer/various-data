module.exports = {
    jobName: 'test',
    options: null,
    handler(job, done) {
        console.log('test', Date.now());
    }
};