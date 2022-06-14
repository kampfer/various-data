import React from 'react';
import { List, Checkbox } from 'antd';
import VirtualList from 'rc-virtual-list';

import 'antd/dist/antd.css';
import './index.css';

const data = Array.from({ length : 10000 }).map((d, i) => ({
    author: 'liaowei',
    title: `测试新闻${i}`,
    date: Date.now() + 100
}));

export default class App extends React.Component {
    render() {
        return (
            <List className="news-list">
                <VirtualList
                    data={data}
                    height={window.innerHeight}
                    itemHeight={47}
                    itemKey='date'
                >
                    {(item) => (
                        <List.Item key={item.date}>
                            <Checkbox>{item.title}</Checkbox>
                        </List.Item>
                    )}
                </VirtualList>
            </List>
        );
    }
}