import React from 'react';
import { Table, Space } from 'antd';
import indicators from './indicators.js';

import 'antd/dist/antd.css';

const columns = [
    {
        title: '名称',
        key: 'name',
        dataIndex: 'name',
    },
    {
        title: '描述',
        key: 'desc',
        dataIndex: 'desc',
    },
    {
        title: '操作',
        key: 'action',
        render: () => (
            <Space size="middle">
                <a>查看</a>
                <a>更新</a>
            </Space>
        )
    }
];

export default class IndicatorList extends React.Component {

    // constructor(props) {
    //     super(props);
    // }

    render() {
        return (
            <Table dataSource={indicators} columns={columns} pagination={{hideOnSinglePage: true}}/>
        );
    }

}