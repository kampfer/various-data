import React from 'react';
import { List, Checkbox } from 'antd';
import VirtualList from 'rc-virtual-list';
import { connect } from "react-redux";

import { getNews, toggleNews } from '../store/actions.js';

import 'antd/dist/antd.css';
import './index.css';

class App extends React.Component {

    componentDidMount() {
        this.props.getNews();
    }

    render() {
        const { news, toggleNews } = this.props;
        return (
            <List className="news-list">
                <VirtualList
                    data={news}
                    height={window.innerHeight}
                    itemHeight={47}
                    itemKey='date'
                >
                    {(item, index) => (
                        <List.Item key={item.date}>
                            <Checkbox onChange={() => toggleNews(index)} checked={item.checked}>{item.title}</Checkbox>
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
