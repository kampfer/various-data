import React from 'react';
import {
    Table,
    Space
} from 'antd';
import indicators from './indicators.js';
import {
    Link
} from "react-router-dom";
  
import 'antd/dist/antd.css';

const updateIndicator = (name) => {
    if (name) {
        fetch(`/api/update?name=${name}`)
            .then(res => res.json())
            .then(json => {
                if (json.code === 200) alert('更新成功！');
            });
    }
};

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
        render: (text, record, /*index*/) => (
            <Space size='middle'>
                <Link to={`/indicator/${record.name}`}>查看</Link>
                <a onClick={() => updateIndicator(record.name)}>更新</a>
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
            <Table dataSource={indicators} columns={columns} pagination={{hideOnSinglePage: true}} rowKey='name'/>
        );
    }

}
