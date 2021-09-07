import React from 'react';

export default class FrFdrGraph extends React.Component {

    componentDidMount() {
        fetch('data/fr_fdr.json')
            .then(response => response.json())
            .then(({ data }) => {
                this.chart = Highcharts.chart('FrFdrGraph', {
                    chart: {
                        width: window.innerWidth,
                        height: window.innerHeight,
                    },
                    title: {
                        text: '回购定盘利率和银银间回购定盘利率'
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
                        name: 'FDR007',
                        data: data.map(d => ({
                            x: d.date,
                            y: parseFloat(d.FDR007, 10)
                        }))
                    }, {
                        name: 'FR007',
                        data: data.map(d => ({
                            x: d.date,
                            y: parseFloat(d.FR007, 10)
                        })),
                    }],
                });
            });
    }

    componentWillUnmount() {
        this.chart.destroy();
    }

    render() {
        return <div id='FrFdrGraph'></div>;
    }

}