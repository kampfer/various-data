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

// function AppState(app) {
//     const indicatorList = [];
//     return {
//         indicatorList,
//         addIndicator(values) {
//             return fetch(`/api/addIndicator`, {
//                 body: JSON.stringify(values),
//                 method: 'POST',
//                 headers: {
//                     'content-type': 'application/json'
//                 }
//             })
//             .then(res => res.json())
//             .then(({ code, msg, data }) => {
//                 if (code === 200) {
//                     app.setState({ indicatorList: [...indicatorList, data] });
//                     return data;
//                 }
//             });
//         },
//         deleteIndicator() {},
//         updateIndicator() {},
//         crawlIndicator() {}
//     };
// }

class AppState {

    constructor(app) {
        this.app = app;
        this.indicatorList = [];
    }

    getIndicatorList() {}

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
                const newIndicatorList = [...this.indicatorList, data];
                this.indicatorList = newIndicatorList;
                this.app.setState({ indicatorList: newIndicatorList });
                return data;
            } else {
                return Promise.reject(msg);
            }
        });
    }

    deleteIndicator() {}

    updateIndicator() {}

    crawlIndicator() {}

}

export default class App extends React.Component {

    constructor(props) {
        super(props);
        this.state = new AppState(this);
    }

    // addIndicator(data) {
    //     const { indicatorList } = this.state;
    //     this.setState({ indicatorList: [...indicatorList, data] });
    // }

    // deleteIndicator(id) {
    //     const { indicatorList } = this.state;
    //     const index = indicatorList.findIndex(d => d.id === id);
    //     indicatorList.splice(index, 1);
    //     this.setState({ indicatorList: [...indicatorList] });
    // }

    componentDidMount() {
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data }) => {
                this.setState({ indicatorList: data });
            });
    }

    render() {
        return (
            <Router>
                <Switch>
                    <Route exact path='/'>
                        <Redirect to='/indicators' />
                    </Route>
                    <Route path='/indicators'>
                        <IndicatorList indicatorList={this.state} />
                    </Route>
                    <Route path='/indicator/table'>
                        <IndicatorTableRouter indicatorList={this.state} />
                    </Route>
                    <Route path='/indicator/graph/:id'>
                        <IndicatorGraphRouter indicatorList={this.state} />
                    </Route>
                </Switch>
            </Router>
        );
    }

}