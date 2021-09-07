import React from 'react';
import {
    Table,
    Space,
    Spin,
    message,
    Button,
} from 'antd';
import {
    Link
} from "react-router-dom";

import 'antd/dist/antd.css';
import './IndicatorList.css';

export default class IndicatorList extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            indicatorList: [],
            columns: [
                {
                    title: '名称',
                    dataIndex: 'name',
                },
                {
                    title: '描述',
                    dataIndex: 'desc',
                },
                {
                    title: '操作',
                    dataIndex: 'action',
                    render: (text, record, /*index*/) => (
                        <Space size='middle'>
                            <Link to={`/indicator/graph/${record.name}`}>查看图表</Link>
                            <Link to={`/indicator/table/${record.name}`}>查看表格</Link>
                            <a onClick={() => this.updateIndicator(record.name)}>更新</a>
                        </Space>
                    )
                }
            ],
            loading: false,
        };
    }

    addRow = () => {}

    updateIndicator = (name) => {
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

    componentDidMount() {
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data }) => {
                this.setState({ indicatorList: data });
            });
    }

    render() {
        const { indicatorList, columns } = this.state;
        return (
            <Spin spinning={this.state.loading}>
                <div className="indicator-list-container">
                    <Button
                        onClick={this.addRow}
                        type='primary'
                        className='add-row-btn'
                    >
                        新增指标
                    </Button>
                    <Table dataSource={indicatorList} columns={columns} pagination={{hideOnSinglePage: true}} rowKey='name' bordered />
                </div>
            </Spin>
        );
    }

}
