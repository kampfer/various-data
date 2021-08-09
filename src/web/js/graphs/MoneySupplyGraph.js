import React, { useEffect } from 'react';

export default function MoneySupplyGraph() {

    useEffect(() => {
        const chart = (async () => {
            const { data } = await fetch('data/moneySupply.json')
                .then(response => response.json());

            return Highcharts.chart('MoneySupplyGraph', {
                chart: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                },
                title: {
                    text: '中国 货币供应量'
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
                        day: '%Y-%m-%d'
                    }
                },
                series: [{
                    name: 'm0',
                    color: 'red',
                    data: data.map(d => ({
                        x: (new Date(d.date)).getTime(),
                        y: parseFloat(d.m0, 10)
                    }))
                }, {
                    name: 'm1',
                    color: 'green',
                    data: data.map(d => ({
                        x: (new Date(d.date)).getTime(),
                        y: parseFloat(d.m1, 10)
                    })),
                }, {
                    name: 'm2',
                    color: 'blue',
                    data: data.map(d => ({
                        x: (new Date(d.date)).getTime(),
                        y: parseFloat(d.m2, 10)
                    })),
                }],
            });
        })();

        return () => chart.destroy();
    });

    return (<div id='MoneySupplyGraph'></div>);

}