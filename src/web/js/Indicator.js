import React from 'react';
import {
    Switch,
    Route,
} from 'react-router-dom';
import BalanceSheetOfMonetaryAuthorityGraph from './graphs/BalanceSheetOfMonetaryAuthorityGraph.js';
import CpiGraph from './graphs/CpiGraph.js';
import FrFdrGraph from './graphs/FrFdrGraph.js';
import MoneySupplyGraph from './graphs/MoneySupplyGraph.js';
import RMBCFETSIndex from './graphs/RMBCFETSIndex.js';
import TicketGraph from './graphs/TicketGraph.js';

export default function IndicatorGraph() {

    return (
        <Switch>
            <Route path='/indicator/cpi'>
                <CpiGraph />
            </Route>
            <Route path='/indicator/moneySupply'>
                <MoneySupplyGraph />
            </Route>
            <Route path='/indicator/ticketPutAndBackStatByMonth'>
                <TicketGraph />
            </Route>
            <Route path='/indicator/fr_fdr'>
                <FrFdrGraph />
            </Route>
            <Route path='/indicator/rmbCFETSIndex'>
                <RMBCFETSIndex />
            </Route>
            <Route path='/indicator/balanceSheetOfMonetaryAuthority'>
                <BalanceSheetOfMonetaryAuthorityGraph />
            </Route>
        </Switch>
    );

}