import React from 'react';
import {
    Table,
    Space,
    Spin,
    message
} from 'antd';
import indicators from './indicators.js';
import {
    Link
} from "react-router-dom";
  
import 'antd/dist/antd.css';
import './IndicatorList.css';

export default class IndicatorList extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            columns: [
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
                            <a onClick={() => this.updateIndicator(record.name)}>更新</a>
                        </Space>
                    )
                }
            ],
            loading: false,
        };

        this.updateIndicator = this.updateIndicator.bind(this);
    }

    updateIndicator(name) {
        if (name) {
            this.setState({loading: true});
            fetch(`/api/update?name=${name}`)
                .then(res => res.json())
                .then(json => {
                    if (json.code === 200) message.success(`${name}更新成功`);
                })
                .finally(() => this.setState({ loading: false }));
        }
    }

    render() {
        return (
            <Spin spinning={this.state.loading}>
                <Table dataSource={indicators} columns={this.state.columns} pagination={{hideOnSinglePage: true}} rowKey='name'/>
            </Spin>
        );
    }

}
