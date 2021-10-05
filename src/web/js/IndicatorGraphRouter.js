import React, { useState, useEffect } from 'react';
import {
    useRouteMatch,
} from 'react-router-dom';
import * as graphs from './graphs/index.js';

export default function IndicatorGraphRouter({ indicatorList }) {

    const { params: { id } } = useRouteMatch();
    const [data, setData] = useState([]);
    const indicator = indicatorList.find(d => d.id === id);

    // Highcharts 中默认开启了UTC（世界标准时间），由于中国所在时区为+8，所以经过 Highcharts 的处理后会减去8个小时。
    Highcharts.setOptions({ global: { useUTC: false } });

    useEffect(() => {
        if (!indicator) return;
        fetch(`data/${indicator.id}.json`)
            .then(response => response.json())
            .then(({ data }) => setData(data));
    }, [indicator]);

    if (indicator) {
        const Graph = graphs[indicator.graph];
        if (Graph) {
            return (
                <Graph indicator={indicator} data={data} />
            );
        } else {
            return '图表不存在';
        }
    } else {
        return '没找到图表';
    }

}