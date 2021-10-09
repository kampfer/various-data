import React, { useEffect } from 'react';

export default function TicketGraph({ data }) {

    useEffect(() => {
        let chart = Highcharts.chart('TicketGraph', {
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
                type: 'line',
                data: data.map(d => ({
                    x: d.date,
                    y: parseFloat(d.accPutIn, 10)
                }))
            }],
        });

        return () => chart && chart.destroy();
    }, [data]);

    return (<div id='TicketGraph'></div>);

}