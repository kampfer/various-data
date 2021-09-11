import React from 'react';
import {
    Switch,
    Route,
    useRouteMatch,
} from 'react-router-dom';
import IndicatorTable from './IndicatorTable.js';

export default function IndicatorTableRouter() {
    const { path } = useRouteMatch();
    return (
        <Switch>
            <Route path={`${path}/:id`} component={IndicatorTable} />
        </Switch>
    );
}