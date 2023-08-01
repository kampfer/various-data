import React from 'react';
import { List } from 'antd';
import VirtualList from 'rc-virtual-list';
import { connect } from 'react-redux';
import EventCard from './EventCard/index.js';

import { getNews, toggleNews } from '../../store/actions.js';

import 'antd/dist/antd.css';

class App extends React.Component {

    componentDidMount() {
        this.props.getNews();
    }

    render() {
        const { news, toggleNews } = this.props;
        return (
            <List split={false}>
                <VirtualList
                    data={news}
                    height={window.innerHeight}
                    itemHeight={47}
                    // itemKey='date'
                >
                    {(item, index) => (
                        <List.Item key={index} style={{ padding: 0 }}>
                            <EventCard data={item} />
                        </List.Item>
                    )}
                </VirtualList>
            </List>
        );
    }
}

const mapStateToProps = state => {
    return { news: state.news };
};

export default connect(mapStateToProps, { getNews, toggleNews })(App);
