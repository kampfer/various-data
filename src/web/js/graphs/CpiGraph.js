import React from 'react';

export default class CpiGraph extends React.Component {

    componentDidMount() {
        fetch('data/cpi.json')
            .then(response => response.json())
            .then(({ data }) => {
                // 倒排数据，再计算累计值
                data.reverse();

                let accValue = 1;
                const accSerie = {
                    name: 'cpi累计',
                    type: 'line',
                    data: data.map(d => ({
                        x: (new Date(d.date.replace(/(\d{4})(\d{2})/, ($0, $1, $2) => `${$1}-${$2}`))).getTime(),
                        y: accValue *= (isNaN(d.cpi) || d.cpi === null) ? 1 : d.cpi / 100,
                    }))
                };

                this.chart = Highcharts.chart('CpiGraph', {
                    chart: {
                        width: window.innerWidth,
                        height: window.innerHeight,
                    },
                    title: {
                        text: '居民消费价格指数(累计)'
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
                    series: [accSerie],
                });
            });
    }

    componentWillUnmount() {
        this.chart.destroy();
    }

    render() {
        return <div id='CpiGraph'></div>;
    }

}