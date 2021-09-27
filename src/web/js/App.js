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
        this.setState({ indicatorList: [...indicatorList, data] });
    }

    deleteIndicator(id) {
        const { indicatorList } = this.state;
        const index = indicatorList.findIndex(d => d.id === id);
        indicatorList.splice(index, 1);
        this.setState({ indicatorList: [...indicatorList] });
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
                        <IndicatorList indicatorList={indicatorList} onAddIndicator={(data) => this.addIndicator(data)} onDeleteIndicator={(id) => this.deleteIndicator(id)} />
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