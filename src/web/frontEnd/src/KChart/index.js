import React from 'react';
import * as echarts from 'echarts';
import moment from 'moment';

import './index.css';

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

function makeCandleChart(data, container) {
    const upColor = 'rgb(235, 84, 84)';
    const downColor = 'rgb(71, 178, 98)';
    const chart = echarts.init(container);
    chart.setOption({
        animation: false,
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
            show: false
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
                left: '100',
                right: '100',
                height: '50%'
            },
            {
                left: '100',
                right: '100',
                top: '70%',
                height: '15%'
            }
        ],
        xAxis: [
            {
                triggerEvent: true,
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
                top: '90%',
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
    // chart.on('selectchanged', (...args) => console.log(args));
    // chart.on('axisareaselected', (...args) => console.log(args));
    chart.on('mouseover', (...args) => console.log(args));
    return chart;
}

export default class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            containerRef: React.createRef()
        };
    }

    componentDidMount() {
        fetch('/stock/sh000001')
            .then(res => res.json())
            .then(res => JSON.parse(res))
            .then(data => {
                data = splitData(data);
                makeCandleChart(data, this.state.containerRef.current);
            });
    }

    render() {
        const { containerRef } = this.state;
        return <div className='k-chart' ref={containerRef}></div>
    }
}
