import React from 'react';
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
            <VirtualList
                data={news}
                height={window.innerHeight}
                itemHeight={100}
            >
                { (item, index) => <EventCard key={item.id} data={item} /> }
            </VirtualList>
        );
    }
}

const mapStateToProps = state => {
    return { news: state.news };
};

export default connect(mapStateToProps, { getNews, toggleNews })(App);
