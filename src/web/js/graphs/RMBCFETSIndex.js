import React, { useEffect } from 'react';

export default function RMBCFETSIndexGraph() {

    useEffect(() => {

        const chart = (async () => {
            const { data } = await fetch('data/rmbCFETSIndex.json')
                .then(response => response.json());

            return Highcharts.chart('RMBCFETSIndexGraph', {
                chart: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                },
                title: {
                    text: 'CFETS人民币汇率指数'
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
                    name: 'CFETS',
                    data: data.map(d => ({
                        x: (new Date(d.date)).getTime(),
                        y: parseFloat(d.indexRate, 10)
                    }))
                }],
            });
        })();

        return () => chart.destroy();
        
    });

    return (<div id='RMBCFETSIndexGraph'></div>);

}