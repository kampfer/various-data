import React, { useEffect } from 'react';

export default function MoneySupplyGraph() {

    useEffect(() => {
        let chart;
        fetch('data/moneySupply.json')
            .then(response => response.json())
            .then(({ data }) => {
                chart = Highcharts.chart('MoneySupplyGraph', {
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
                            day: '%Y-%m-%d',
                            month: '%Y-%m'
                        }
                    },
                    series: [{
                        name: 'm0',
                        color: 'red',
                        data: data.map(d => ({
                            x: d.date,
                            y: parseFloat(d.m0, 10)
                        }))
                    }, {
                        name: 'm1',
                        color: 'green',
                        data: data.map(d => ({
                            x: d.date,
                            y: parseFloat(d.m1, 10)
                        })),
                    }, {
                        name: 'm2',
                        color: 'blue',
                        data: data.map(d => ({
                            x: d.date,
                            y: parseFloat(d.m2, 10)
                        })),
                    }],
                });
            });

        return () => chart && chart.destroy();
    });

    return (<div id='MoneySupplyGraph'></div>);

}