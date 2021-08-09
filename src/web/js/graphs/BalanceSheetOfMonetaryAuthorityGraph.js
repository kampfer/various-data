import React, { useEffect } from 'react';

export default function BalanceSheetOfMonetaryAuthorityGraph() {

    useEffect(() => {
        const chart = (async () => {
            const { data } = await fetch('data/balanceSheetOfMonetaryAuthority.json')
                .then(response => response.json());

            return Highcharts.chart('BalanceSheetOfMonetaryAuthorityGraph', {
                chart: {
                    type: 'area',
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
                series: Object.keys(data[0]).filter(key =>!['date', 'TotalAssets', 'TotalLiabilities'].includes(key)).map((key) => ({
                    name: key,
                    data: data.map(d => {
                        console.log(d);
                        return {
                            x: new Date(d.date.replace('.', '-')).getTime(),
                            y: d[key]
                        };
                    })
                }))
            });
        })();

        return () => chart.destroy();
    });

    return (<div id='BalanceSheetOfMonetaryAuthorityGraph'></div>);

}