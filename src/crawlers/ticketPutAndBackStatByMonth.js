const request = require('./request');

module.exports = async function () {
    const { data } = (await request.post({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bond-publish/TicketPutAndBackMonthRegion',
    })).json();

    const { maxMonth, maxMonthYear, minMonth, minMonthYear } = data.ticketPutAndBackMonthRegion;
    const months = (maxMonthYear - minMonthYear) * 12 + (maxMonth - minMonth) + 1;

    const res = await request.post({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bond-publish/TicketPutAndBackStatByMonth',
        data: {
            startMonth: `${minMonthYear}-${minMonth}`,
            endMonth: `${maxMonthYear}-${maxMonth}`,
            pageSize: months,
            pageNo: 1,
        }
    });

    const json = res.json();
    const list = json.data.resultList.reverse();
    let accPutIn = 0;

    return {
        name: 'ticketPutAndBackStatByMonth',
        description: '央行票据',
        source: 'http://www.chinamoney.com.cn',
        data: list.map(({ date, putIn, back, netPutIn }) => {
            netPutIn = Number(netPutIn);
            accPutIn += netPutIn;
            return {
                date,
                putIn: Number(putIn),
                back: Number(back),
                netPutIn,
                accPutIn,
            }
        })
    };
}