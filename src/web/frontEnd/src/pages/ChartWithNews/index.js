import React from 'react';
import KChart from '../../components/KChart/index.js';
import NewsList from '../../components/NewsList/index.js';

import './index.css';

export default class ChartWithNews extends React.Component {

    componentDidMount() {}

    render() {
        return (
            <div id="ChartWithNews">
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
