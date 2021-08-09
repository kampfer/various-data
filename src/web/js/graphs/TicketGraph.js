import React, { useEffect } from 'react';

export default function TicketGraph() {

    useEffect(async () => {
        const { data } = await fetch('data/ticketPutAndBackStatByMonth.json')
            .then(response => response.json());

        const chart = Highcharts.chart('TicketGraph', {
            chart: {
                width: window.innerWidth,
                height: window.innerHeight,
            },
            title: {
                text: '央行票据'
            },
            xAxis: {
                type: 'datetime',
                tickPixelInterval: window.innerWidth / 10,
                dateTimeLabelFormats: {
                    month: '%Y-%m'
                }
            },
            tooltip: {
                dateTimeLabelFormats: {
                    day: '%Y-%m-%d',
                    month: '%Y-%m'
                }
            },
            series: [{
                name: '央行票据',
                data: data.map(d => ({
                    x: (new Date(d.date)).getTime(),
                    y: parseFloat(d.accPutIn, 10)
                }))
            }],
        });

        return () => chart.destroy();
    });

    return (<div id='TicketGraph'></div>);

}