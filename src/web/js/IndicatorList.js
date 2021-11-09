import React from 'react';
import {
    Table,
    Space,
    Spin,
    message,
    Button,
    Modal,
    Form,
    Input,
    Radio
} from 'antd';
import {
    NavLink
} from "react-router-dom";
import {
    AUTO_UPDATE_INDICATOR,
    MANUAL_UPDATE_INDICATOR,
} from '../../constants/indicatorTypes.js';
import moment from 'moment';

import 'antd/dist/antd.css';
import './IndicatorList.css';

const dateFormat = 'YYYY-MM-DD';

export default class IndicatorList extends React.Component {

    newIndicatorForm = React.createRef()

    constructor(props) {
        super(props);

        this.state = {
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
                    title: '创建时间',
                    dataIndex: 'createTime',
                    render: (text) => moment(text).format(dateFormat),
                    sorter: (a, b) => a.createTime - b.createTime
                },
                {
                    title: '更新时间',
                    dataIndex: 'updateTime',
                    render: (text) => moment(text).format(dateFormat),
                    sorter: (a, b) => a.updateTime - b.updateTime
                },
                {
                    title: '操作',
                    dataIndex: 'action',
                    render: (text, record, /*index*/) => {
                        return (
                            <Space size='middle'>
                                <a onClick={() => this.doEidt(record.id)}>编辑</a>
                                { <NavLink to={`/indicator/graph/${record.id}`}>查看图表</NavLink> }
                                { <NavLink to={`/indicator/table/${record.id}`}>查看表格</NavLink> }
                                { !record.type && <a onClick={() => this.crawlIndicator(record.id)}>更新</a> }
                                <a onClick={() => this.deleteIndicator(record.id)}>删除</a>
                            </Space>
                        );
                    }
                }
            ],
            loading: false,
            newIndicatorVisible: false,
            indicatorFields: []
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
                            this.props.onAddIndicator(data);
                            this.hideNewIndicatorModal();
                        } else {
                            message.error(msg);
                        }
                    })
                    .finally(() => this.setState({ loading: false }));
        });
    }

    crawlIndicator(id) {
        if (id) {
            this.setState({loading: true});
            fetch(`/api/crawlIndicator?id=${id}`)
                .then(res => res.json())
                .then(json => {
                    if (json.code === 200) {
                        message.success(`${id}更新成功`);
                    } else {
                        message.error(json.msg);
                    }
                })
                .finally(() => this.setState({ loading: false }));
        }
    }

    deleteIndicator(id) {
        if (id) {
            this.setState({loading: true});
            fetch(`/api/deleteIndicator?id=${id}`)
                .then(res => res.json())
                .then(json => {
                    if (json.code === 200) {
                        this.props.onDeleteIndicator(id);
                        message.success(`删除成功`);
                    }
                })
                .finally(() => this.setState({ loading: false }));
        }
    }

    showNewIndicatorModal = () => {
        this.setState({ newIndicatorVisible: true });
    }

    hideNewIndicatorModal = () => {
        this.newIndicatorForm.current.resetFields();
        this.setState({ newIndicatorVisible: false });
    }

    doEidt(id) {
        const { indicatorList } = this.props;
        const indicator = indicatorList.find(d => d.id === id);
        this.setState({ 
            indicatorFields: [
                {
                    name: ['name'],
                    value: indicator.name
                },
                {
                    name: ['type'],
                    value: indicator.type
                },
                {
                    name: ['graph'],
                    value: indicator.graph
                },
                {
                    name: ['fieldList'],
                    value: indicator.fieldList
                },
                {
                    name: ['crawler'],
                    value: indicator.crawler
                },
                {
                    name: ['description'],
                    value: indicator.description
                }
            ],
            newIndicatorVisible: true
        });
    }

    render() {
        const { columns, newIndicatorVisible, indicatorFields } = this.state;
        const { indicatorList } = this.props;
        const validateMessages = {
            required: '${label} is required!',
        };
        const indicatorType = (indicatorFields.find(d => d.name[0] === 'type') || {}).value;

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
                            fields={indicatorFields}
                            onChange={(newFields) => {
                                this.setState({ indicatorFields: newFields });
                            }}
                            preserve={false}
                        >
                            <Form.Item name="name" label="指标名称" rules={[{ required: true }]}>
                                <Input />
                            </Form.Item>
                            <Form.Item name="type" label="维护方式" rules={[{ required: true }]}>
                                <Radio.Group>
                                    <Radio value={AUTO_UPDATE_INDICATOR}>自动</Radio>
                                    <Radio value={MANUAL_UPDATE_INDICATOR}>手动</Radio>
                                </Radio.Group>
                            </Form.Item>
                            <Form.Item name="graph" label="图表名" rules={[{ required: true }]}>
                                <Input />
                            </Form.Item>
                            {
                                indicatorType === MANUAL_UPDATE_INDICATOR &&
                                <Form.Item name="fieldList" label="字段列表" rules={[{ required: true }]}>
                                    <Input />
                                </Form.Item>
                            }
                            {
                                indicatorType === AUTO_UPDATE_INDICATOR &&
                                <Form.Item name="crawler" label="爬虫名" rules={[{ required: true }]}>
                                    <Input />
                                </Form.Item>
                            }
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
