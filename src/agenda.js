const fs = require('fs');
const path = require('path');
const Agenda = require('agenda');

const agenda = new Agenda({
    db: { address: 'mongodb://127.0.0.1:27017/agendaDb' },
    processEvery: '1 second'
});

agenda.on('ready', () => {
    console.log((new Date()).toLocaleString(), 'agenda ready');
});

agenda.on('error', (error) => {
    console.log((new Date()).toLocaleString(), 'agenda error: ', error);
});

agenda.on('start', job => {
    console.log((new Date()).toLocaleString(), `Job <${job.attrs.name}> starting`);
});
agenda.on('success', job => {
    console.log((new Date()).toLocaleString(), `Job <${job.attrs.name}> succeeded`);
});
agenda.on('fail', (error, job) => {
    console.log((new Date()).toLocaleString(), `Job <${job.attrs.name}> failed:`, error);
});

const jobsDir = path.resolve(__dirname, 'jobs');
const jobs = fs.readdirSync(jobsDir).map(value => require(path.resolve(jobsDir, value)));

jobs.forEach(job => {
    if (job.options) {
        agenda.define(job.jobName, job.options, job.handler);
    } else {
        agenda.define(job.jobName, job.handler);
    }
});

agenda.start().then(() => {
    jobs.forEach(async (job) => {
        if (job.jobType === 'every') {
            await agenda.every(job.time, job.jobName, job.data, job.options);
        } else if (job.jobType === 'schedule') {
            await agenda.schedule(job.time, job.jobName, job.data);
        } else if (job.jobType === 'now') {
            await agenda.now(job.jobName, job.data);
        }
    });
});