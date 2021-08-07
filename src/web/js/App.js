import React from 'react';
import {
    HashRouter as Router,
    Switch,
    Route,
} from 'react-router-dom';
import IndicatorList from './IndicatorList.js';

export default class App extends React.Component {

    constructor(props) {
        super(props);
    }

    render() {
        return (
            <Router>
                <Switch>
                    <Route path="/indicators">
                        <IndicatorList></IndicatorList>
                    </Route>
                    <Route path="/indicator">
                        indicator
                    </Route>
                </Switch>
            </Router>
        );
    }

}