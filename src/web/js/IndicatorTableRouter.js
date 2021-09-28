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
                render={({ match: { params: { id }}}) => <IndicatorTable id={id} indicatorList={indicatorList} />}
            />
        </Switch>
    );
}