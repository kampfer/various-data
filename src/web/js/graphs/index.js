import React from 'react';
import {
    Switch,
    Route,
    useRouteMatch
} from 'react-router-dom';
import {
    Empty
} from 'antd';
import BalanceSheetOfMonetaryAuthorityGraph from './BalanceSheetOfMonetaryAuthorityGraph.js';
import CpiGraph from './CpiGraph.js';
import FrFdrGraph from './FrFdrGraph.js';
import MoneySupplyGraph from './MoneySupplyGraph.js';
import CFETSRMBIndexGraph from './CFETSRMBIndexGraph.js';
import TicketGraph from './TicketGraph.js';

export default function IndicatorGraphRouter() {

    let { path } = useRouteMatch();

    // Highcharts 中默认开启了UTC（世界标准时间），由于中国所在时区为+8，所以经过 Highcharts 的处理后会减去8个小时。
    Highcharts.setOptions({ global: { useUTC: false } });

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
            <Route path={`${path}/CFETSRMBIndex`}>
                <CFETSRMBIndexGraph />
            </Route>
            <Route path={`${path}/balanceSheetOfMonetaryAuthority`}>
                <BalanceSheetOfMonetaryAuthorityGraph />
            </Route>
            <Route path='*'>
                <Empty />
          </Route>
        </Switch>
    );

}