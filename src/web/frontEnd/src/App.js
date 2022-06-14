import React from 'react';
import KChart from './KChart/index.js';
import NewsList from './NewsList/index.js';

import './main.css';

export default class App extends React.Component {

    componentDidMount() {}

    render() {
        return (
            <div id="app">
                <div className="left">
                    <KChart></KChart>
                </div>
                <div className="right">
                    <NewsList></NewsList>
                </div>
            </div>
        );
    }

}
