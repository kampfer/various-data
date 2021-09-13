import React from 'react';
import {
    Table,
    Space,
    Spin,
    message,
    Button,
    Modal,
    Form,
    Input
} from 'antd';
import {
    Link
} from "react-router-dom";

import 'antd/dist/antd.css';
import './IndicatorList.css';

export default class IndicatorList extends React.Component {

    newIndicatorForm = React.createRef()

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
                    dataIndex: 'description',
                },
                {
                    title: '操作',
                    dataIndex: 'action',
                    render: (text, record, /*index*/) => (
                        <Space size='middle'>
                            <Link to={`/indicator/graph/${record.id}`}>查看图表</Link>
                            <Link to={`/indicator/table/${record.id}`}>查看表格</Link>
                            <a onClick={() => this.updateIndicator(record.id)}>更新</a>
                        </Space>
                    )
                }
            ],
            loading: false,
            newIndicatorVisible: false,
        };
    }

    addIndicator = () => {
        this.newIndicatorForm.current.validateFields()
            .then((values) => {
                this.setState({ loading: true });
                fetch(`/api/addIndicator`, {
                    body: JSON.stringify(values),
                    method: 'POST',
                    headers: {
                        'content-type': 'application/json'
                    }
                })
                    .then(res => res.json())
                    .then(({ code, msg, data }) => {
                        if (code === 200) {
                            const { indicatorList } = this.state;
                            this.setState({ indicatorList: [...indicatorList, data]});
                            this.hideNewIndicatorModal();
                        } else {
                            message.error(msg);
                        }
                    })
                    .finally(() => this.setState({ loading: false }));
        });
    }

    updateIndicator = (id) => {
        if (id) {
            this.setState({loading: true});
            fetch(`/api/update?name=${id}`)
                .then(res => res.json())
                .then(json => {
                    if (json.code === 200) message.success(`${id}更新成功`);
                })
                .finally(() => this.setState({ loading: false }));
        }
    }

    showNewIndicatorModal = () => {
        this.setState({ newIndicatorVisible: true });
    }

    hideNewIndicatorModal = () => {
        this.setState({ newIndicatorVisible: false });
    }

    componentDidMount() {
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data }) => {
                this.setState({ indicatorList: data });
            });
    }

    render() {
        const { indicatorList, columns, newIndicatorVisible } = this.state;
        const validateMessages = {
            required: '${label} is required!',
        };

        return (
            <Spin spinning={this.state.loading}>
                <div className="indicator-list-container">
                    <Button
                        onClick={this.showNewIndicatorModal}
                        type='primary'
                        className='add-row-btn'
                    >
                        新增指标
                    </Button>
                    <Table dataSource={indicatorList} columns={columns} pagination={{hideOnSinglePage: true}} rowKey='name' bordered />
                    <Modal
                        title="新增指标"
                        visible={newIndicatorVisible}
                        onOk={this.addIndicator}
                        onCancel={this.hideNewIndicatorModal}
                        okText="确认"
                        cancelText="取消"
                    >
                        <Form
                            name="newIndicator"
                            ref={this.newIndicatorForm}
                            labelCol={{ span: 4 }}
                            wrapperCol={{ span: 18 }}
                            validateMessages={validateMessages}
                        >
                            <Form.Item name="name" label="名称" rules={[{ required: true }]}>
                                <Input />
                            </Form.Item>
                            <Form.Item name="fieldList" label="字段列表" rules={[{ required: true }]}>
                                <Input />
                            </Form.Item>
                            <Form.Item name="description" label="描述">
                                <Input.TextArea />
                            </Form.Item>
                        </Form>
                    </Modal>
                </div>
            </Spin>
        );
    }

}
