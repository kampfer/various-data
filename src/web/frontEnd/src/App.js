import React from 'react';
import * as echarts from 'echarts';
import moment from 'moment';

function splitData(data) {

    const changes = [];
    data.data.forEach((d, i) => {
      if (i === 0) {
        changes.push(0);
      } else {
        changes.push((d[3] - data.data[i - 1][3]) / d[3]);
      }
    });

    return {
        dates: data.index.map(d => moment(d).format('YYYY-MM-DD')),
        // open close low high
        values: data.data.map(d => [d[0], d[3], d[2], d[1]]),
        volumes: data.data.map((d, i) => [i, d[4], d[0] > d[3] ? 1 : -1]),
        changes
    };
}

function makeCandleChart(data) {
    const upColor = 'rgb(235, 84, 84)';
    const downColor = 'rgb(71, 178, 98)';
    const chart = echarts.init(document.getElementById('k-chart'));
    chart.setOption({
        animation: false,
        // legend: {
        //   bottom: 10,
        //   left: 'center',
        //   data: ['Dow-Jones index', 'MA5', 'MA10', 'MA20', 'MA30']
        // },
        tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'cross'
        },
        borderWidth: 1,
        borderColor: '#ccc',
        padding: 10,
        textStyle: {
            color: '#000'
        },
        position: function (pos, params, el, elRect, size) {
            const obj = {
            top: 10
            };
            obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
            return obj;
        },
        // formatter(param) {
        //   console.log(param);
        //   const index = param[0].dataIndex;
        //   return [`涨跌幅: ${data.changes[index]}`].join('');
        // }
        // extraCssText: 'width: 170px'
        },
        axisPointer: {
        link: [
            {
            xAxisIndex: 'all'
            }
        ],
        label: {
            backgroundColor: '#777'
        }
        },
        toolbox: {
        feature: {
            dataZoom: {
            yAxisIndex: false
            },
            brush: {
            type: ['lineX', 'clear']
            }
        }
        },
        brush: {
        xAxisIndex: 'all',
        brushLink: 'all',
        outOfBrush: {
            colorAlpha: 0.1
        }
        },
        visualMap: {
        show: false,
        seriesIndex: 1,
        dimension: 2,
        pieces: [
            {
            value: 1,
            color: downColor
            },
            {
            value: -1,
            color: upColor
            }
        ]
        },
        grid: [
        {
            left: '10%',
            right: '8%',
            height: '50%'
        },
        {
            left: '10%',
            right: '8%',
            top: '63%',
            height: '16%'
        }
        ],
        xAxis: [
        {
            type: 'category',
            data: data.dates,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax',
            axisPointer: {
            z: 100
            }
        },
        {
            type: 'category',
            gridIndex: 1,
            data: data.dates,
            boundaryGap: false,
            axisLine: { onZero: false },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            min: 'dataMin',
            max: 'dataMax'
        }
        ],
        yAxis: [
        {
            scale: true,
            splitArea: {
            show: true
            }
        },
        {
            scale: true,
            gridIndex: 1,
            splitNumber: 2,
            axisLabel: { show: false },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false }
        }
        ],
        dataZoom: [
        {
            type: 'inside',
            xAxisIndex: [0, 1],
            start: 98,
            end: 100
        },
        {
            show: true,
            xAxisIndex: [0, 1],
            type: 'slider',
            top: '85%',
            start: 98,
            end: 100
        }
        ],
        series: [
        {
            name: '上证指数',
            type: 'candlestick',
            data: data.values
        },
        {
            name: 'Volume',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: data.volumes
        }
        ]
    });
}

export default class App extends React.Component {

    componentDidMount() {
        fetch('/stock/sh000001')
            .then(res => res.json())
            .then(res => JSON.parse(res))
            .then(data => {
                data = splitData(data);
                makeCandleChart(data);
            });
                
    }

    render() {
        return (
            <>
                <div id="k-chart"></div>
                <div id="news-list"></div>
            </>
        );
    }

}
