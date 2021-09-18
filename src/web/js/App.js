import React from 'react';
import {
    HashRouter as Router,
    Switch,
    Route,
    Redirect,
} from 'react-router-dom';
import IndicatorList from './IndicatorList.js';
import IndicatorGraphRouter from './IndicatorGraphRouter.js';
import IndicatorTableRouter from './IndicatorTableRouter.js';

export default class App extends React.Component {

    constructor(props) {
        super(props);
        this.state = { indicatorList: [] };
    }

    addIndicator(data) {
        const { indicatorList } = this.state;
        this.setState({ indicatorList: [...indicatorList, data]});
    }

    componentDidMount() {
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data }) => {
                this.setState({ indicatorList: data });
            });
    }

    render() {
        const { indicatorList } = this.state;
        return (
            <Router>
                <Switch>
                    <Route exact path='/'>
                        <Redirect to='/indicators' />
                    </Route>
                    <Route path='/indicators'>
                        <IndicatorList indicatorList={indicatorList} onAddIndicator={this.addIndicator}/>
                    </Route>
                    <Route path='/indicator/table'>
                        <IndicatorTableRouter indicatorList={indicatorList} />
                    </Route>
                    <Route path='/indicator/graph'>
                        <IndicatorGraphRouter indicatorList={indicatorList} />
                    </Route>
                </Switch>
            </Router>
        );
    }

}