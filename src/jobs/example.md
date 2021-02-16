```js
module.exports = {
    jobName: String,    // 任务名，自己定义即可
    jobType: String,    // 任务类型，支持三种：every, schedule, now
    time: human-interval,   // 任务重复周期，只有every和schedule任务支持
    handler: Function,  // 任务函数，执行具体操作。完成后必须调用done。
    options: Object,    // 任务配置
    data: Object,       // 执行时需要使用的额外数据。
}
```