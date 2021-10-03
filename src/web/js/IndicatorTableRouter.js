import React from 'react';
import {
    Switch,
    Route,
    useRouteMatch,
} from 'react-router-dom';
import IndicatorTable from './tables/IndicatorTable.js';

export default function IndicatorTableRouter({ indicatorList }) {
    const { path } = useRouteMatch();
    return (
        <Switch>
            <Route
                path={`${path}/:id`}
                render={({ match: { params: { id }}}) => {
                    const indicator = indicatorList.find(d => d.id === id);
                    if (indicator) {
                        return <IndicatorTable indicator={indicator} />;
                    } else {
                        return '指标数据不存在';
                    }
                }}
            />
        </Switch>
    );
}