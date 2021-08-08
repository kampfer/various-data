import React from 'react';
import {
    HashRouter as Router,
    Switch,
    Route,
    Redirect,
} from 'react-router-dom';
import IndicatorList from './IndicatorList.js';
import Indicator from './Indicator.js';

export default class App extends React.Component {

    // constructor(props) {
    //     super(props);
    // }

    render() {
        return (
            <Router>
                <Switch>
                    <Route exact path='/'>
                        <Redirect to='/indicators' />
                    </Route>
                    <Route path='/indicators'>
                        <IndicatorList />
                    </Route>
                    <Route path='/indicator/:name'>
                        <Indicator />
                    </Route>
                </Switch>
            </Router>
        );
    }

}