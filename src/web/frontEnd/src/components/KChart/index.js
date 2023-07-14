import React from 'react';
import * as echarts from 'echarts';
import { connect } from "react-redux";
import { getStock } from '../../store/actions.js';
import moment from 'moment';

import './index.css';

class KChart extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            containerRef: React.createRef()
        };
    }

    initEchartsInstance() {
        echarts.init(this.state.containerRef.current);
    }

    getEchartsInstance() {
        return echarts.getInstanceByDom(this.state.containerRef.current);
    }

    makeEchartsOption() {
        const { dates, values: prices, volumes } = this.props.stock;
        const newsGroup = this.props.checkedNews.reduce((group, news) => {
            const date = moment(news.date).format('YYYY-MM-DD');
            if (!group[date]) group[date] = [];
            group[date].push(news);
            return group;
        }, {});
        const markPoints = [];
        Object.entries(newsGroup).forEach(([key, arr]) => {
            const index = dates.indexOf(key);
            if (index > -1) {
                markPoints.push({
                    name: key,
                    coord: [key, prices[index][3]],
                    count: arr.length
                });
            }
        });
        return {
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
                        color: 'rgb(71, 178, 98)'
                    },
                    {
                        value: -1,
                        color: 'rgb(235, 84, 84)'
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
                    data: dates,
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
                    data: dates,
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
                    name: 'stock code',
                    type: 'candlestick',
                    data: prices,
                    markPoint: {
                        label: {
                            formatter: function (param) {
                                return param.data.count;
                            }
                        },
                        data: markPoints
                    }
                },
                {
                    name: 'Volume',
                    type: 'bar',
                    xAxisIndex: 1,
                    yAxisIndex: 1,
                    data: volumes
                }
            ]
        };
    }

    updateEchartsOption(option, notMerge = false, lazyUpdate = false) {
        const echartsInstance = this.getEchartsInstance();
        echartsInstance.setOption(option, notMerge, lazyUpdate);
    }

    componentDidMount() {
        if (!this.getEchartsInstance()) {
            this.initEchartsInstance();
        }
        this.props.getStock('sh000001');
    }

    componentDidUpdate(prevProps, prevState) {
        const { stock, checkedNews } = this.props;
        if (stock && stock.values && checkedNews) {
            const option = this.makeEchartsOption();
            this.updateEchartsOption(option);
        }
    }

    render() {
        const { containerRef } = this.state;
        return <div className='k-chart' ref={containerRef}></div>
    }
}

export default connect((state) => ({ stock: state.stock, checkedNews: state.news.filter(d => d.checked) }), { getStock })(KChart);