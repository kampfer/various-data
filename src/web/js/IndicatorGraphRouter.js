import React from 'react';
import {
    Switch,
    Route,
    useRouteMatch,
} from 'react-router-dom';
import * as graphs from './graphs/index.js';

export default function IndicatorGraphRouter() {

    let { path } = useRouteMatch();

    // Highcharts 中默认开启了UTC（世界标准时间），由于中国所在时区为+8，所以经过 Highcharts 的处理后会减去8个小时。
    Highcharts.setOptions({ global: { useUTC: false } });

    return (
        <Switch>
            { Object.entries(graphs).map(([name, component]) => <Route path={`${path}/${name}`} component={component} key={name} />) }
            <Route path='*'>
                <div>找不到图表</div>
            </Route>
        </Switch>
    );

}