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
                    data: data.map(d => {
                        accValue *= (isNaN(d.cpi) || d.cpi === null) ? 1 : d.cpi / 100;
                        return accValue;
                    })
                };

                // 基于准备好的dom，初始化echarts实例
                this.chart = echarts.init(document.getElementById('CpiGraph'), null, {
                    width: window.innerWidth,
                    height: window.innerHeight,
                });

                // 指定图表的配置项和数据
                var option = {
                    title: {
                        text: '居民消费价格指数(累计)',
                        // left: 'center'
                    },
                    tooltip: {},
                    legend: {
                        data:['cpi累计']
                    },
                    xAxis: {
                        type: 'category',
                        data: data.map(d => d.date.replace(/(\d{4})(\d{2})/, ($0, $1, $2) => `${$1}-${$2}`)),
                    },
                    yAxis: {},
                    series: [accSerie]
                };

                // 使用刚指定的配置项和数据显示图表。
                this.chart.setOption(option);
            });
    }

    componentWillUnmount() {
        this.chart.dispose();
    }

    render() {
        return <div id='CpiGraph'></div>;
    }

}