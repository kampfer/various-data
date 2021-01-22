const request = require('./request');

module.exports = async function () {
    const { data } = await request.post({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bond-publish/TicketPutAndBackMonthRegion',
    });

    const { maxMonth, maxMonthYear, minMonth, minMonthYear } = data.ticketPutAndBackMonthRegion;
    const months = (maxMonthYear - minMonthYear) * 12 + (maxMonth - minMonth) + 1;

    return request.post({
        url: 'http://www.chinamoney.com.cn/ags/ms/cm-u-bond-publish/TicketPutAndBackStatByMonth',
        data: {
            startMonth: `${minMonthYear}-${minMonth}`,
            endMonth: `${maxMonthYear}-${maxMonth}`,
            pageSize: months,
            pageNo: 1,
        }
    });
}