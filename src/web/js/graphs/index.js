import React from 'react';
import {
    Switch,
    Route,
    useRouteMatch,
} from 'react-router-dom';
import BalanceSheetOfMonetaryAuthorityGraph from './BalanceSheetOfMonetaryAuthorityGraph.js';
import CpiGraph from './CpiGraph.js';
import FrFdrGraph from './FrFdrGraph.js';
import MoneySupplyGraph from './MoneySupplyGraph.js';
import RMBCFETSIndex from './RMBCFETSIndex.js';
import TicketGraph from './TicketGraph.js';

export default function IndicatorGraphRouter() {

    let { path } = useRouteMatch();

    return (
        <Switch>
            <Route path={`${path}/cpi`}>
                <CpiGraph />
            </Route>
            <Route path={`${path}/moneySupply`}>
                <MoneySupplyGraph />
            </Route>
            <Route path={`${path}/ticketPutAndBackStatByMonth`}>
                <TicketGraph />
            </Route>
            <Route path={`${path}/fr_fdr`}>
                <FrFdrGraph />
            </Route>
            <Route path={`${path}/rmbCFETSIndex`}>
                <RMBCFETSIndex />
            </Route>
            <Route path={`${path}/balanceSheetOfMonetaryAuthority`}>
                <BalanceSheetOfMonetaryAuthorityGraph />
            </Route>
        </Switch>
    );

}