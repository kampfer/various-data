const fs = require('fs');
const path = require('path');
const Agenda = require('agenda');

const agenda = new Agenda({
    db: { address: 'mongodb://127.0.0.1/agendaDb' },
    processEvery: '5 seconds'
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

(async function() {
    await agenda.start();
    await agenda.every('1 minutes', jobs[0].jobName);
})();