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

        this.state = {
            indicatorList: [],
            getIndicatorList: () => {
                return fetch(`/api/getIndicatorList`)
                    .then(res => res.json())
                    .then(({ data }) => {
                        this.setState({ indicatorList: data });
                        return data;
                    });
            },
            addIndicator(values) {
                return fetch(`/api/addIndicator`, {
                        body: JSON.stringify(values),
                        method: 'POST',
                        headers: {
                            'content-type': 'application/json'
                        }
                    })
                    .then(res => res.json())
                    .then(({ code, msg, data }) => {
                        if (code === 200) {
                            this.app.setState({ 
                                indicatorList: [...this.state.indicatorList, data] 
                            });
                            return data;
                        } else {
                            return Promise.reject(msg);
                        }
                    });
            },
            deleteIndicator(id) {
                return fetch(`/api/deleteIndicator?id=${id}`)
                    .then(res => res.json())
                    .then(json => {
                        if (json.code === 200) {
                            const { indicatorList } = this.state;
                            const index = indicatorList.findIndex(d => d.id === id);
                            const item = indicatorList.splice(index, 1);
                            this.setState({ indicatorList: [...indicatorList] });
                            return item;
                        } else {
                            return Promise.reject(json.msg);
                        }
                    });
            },
            updateIndicator() {},
            crawlIndicator(id) {
                return fetch(`/api/crawlIndicator?id=${id}`)
                    .then(res => res.json())
                    .then(json => {
                        if (json.code === 200) {
                            const { indicatorList } = this.state;
                            const index = indicatorList.findIndex(d => d.id === id);
                            indicatorList.splice(index, 1, json.data);
                            this.setState({ indicatorList: [...indicatorList] });
                            return json.data;
                        } else {
                            return Promise.reject(json.msg);
                        }
                    });
            }
        };
    }

    componentDidMount() {
        this.state.getIndicatorList();
    }

    render() {
        return (
            <Router>
                <Switch>
                    <Route exact path='/'>
                        <Redirect to='/indicators' />
                    </Route>
                    <Route path='/indicators'>
                        <IndicatorList {...this.state} />
                    </Route>
                    <Route path='/indicator/table'>
                        <IndicatorTableRouter {...this.state} />
                    </Route>
                    <Route path='/indicator/graph/:id'>
                        <IndicatorGraphRouter {...this.state} />
                    </Route>
                </Switch>
            </Router>
        );
    }

}