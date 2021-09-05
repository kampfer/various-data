import React from 'react';
import {
    HashRouter as Router,
    Switch,
    Route,
    Redirect,
} from 'react-router-dom';
import IndicatorList from './IndicatorList.js';
import IndicatorGraphRouter from './graphs/index.js';
import IndicatorTableRouter from './tables/index.js';

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
                    <Route path='/indicator/table'>
                        <IndicatorTableRouter />
                    </Route>
                    <Route path='/indicator/graph'>
                        <IndicatorGraphRouter />
                    </Route>
                </Switch>
            </Router>
        );
    }

}