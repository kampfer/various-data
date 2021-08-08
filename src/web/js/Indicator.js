import React from 'react';
import {
    Switch,
    Route,
} from 'react-router-dom';
import CpiGraph from './graphs/CpiGraph.js';
import FrFdrGraph from './graphs/FrFdrGraph.js';

export default function IndicatorGraph() {

    return (
        <Switch>
            <Route path='/indicator/cpi'>
                <CpiGraph />
            </Route>
            <Route path='/indicator/moneySupply'>
                <CpiGraph />
            </Route>
            <Route path='/indicator/ticketPutAndBackStatByMonth'>
                <CpiGraph />
            </Route>
            <Route path='/indicator/fr_fdr'>
                <FrFdrGraph />
            </Route>
            <Route path='/indicator/rmbCFETSIndex'>
                <CpiGraph />
            </Route>
            <Route path='/indicator/balanceSheetOfMonetaryAuthority'>
                <CpiGraph />
            </Route>
        </Switch>
    );

}