/* eslint-disable react/prop-types */

import React from 'react';
import {
    Table,
    Button,
    Form,
    InputNumber,
    DatePicker,
    message
} from 'antd';
import moment from 'moment';
import {
    MANUAL_UPDATE_INDICATOR
} from '../../../constants/indicatorTypes.js';

const genKey = (() => {
    let i = 0;
    return (d) => {
        d._key = i++;
        return d;
    };
})();

const dateFormat = 'YYYY-MM-DD';

export default class IndicatorTable extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            indicator: null,
            columns: [],
            data: [],
            canAdd: false,
            editingKey: '',
        };
        this.formRef = React.createRef();
    }

    addRow = () => {
        const { columns, data } = this.state;
        const newData = {};
        genKey(newData);
        columns.forEach(d => {
            if (d.dataIndex === 'date') {
                newData.date = moment().format('YYYY-MM-DD');
            } else if (d.dataIndex !== 'operation') {
                newData[d.dataIndex] = null;
            }
        });
        this.setState({
            data: [...data, newData],
            editingKey: newData._key
        });
    }

    save = async () => {
        const { editingKey, data } = this.state;
        this.formRef.current.validateFields().then((values) => {
            const newData = [...data];
            const index = newData.findIndex(d => d._key === editingKey);
            values.date = values.date.format(dateFormat);
            if (index > -1) {
                const item = newData[index];
                newData.splice(index, 1, { ...item, ...values });
            } else {
                newData.push(genKey(values));
            }
            this.setState({ data: newData, editingKey: '' });
            this.formRef.current.resetFields();
        });
    }

    edit(key) {
        this.setState({ editingKey: key });
    }

    isEditing(record) {
        return record._key === this.state.editingKey;
    }

    componentDidMount() {
        const { id } = this.props.match.params;
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data: indicatorList }) => indicatorList.find(d => d.id === id))
            .then((indicator) => {
                if (indicator) {
                    return fetch(`data/${id}.json`)
                        .then(response => response.json())
                } else {
                    return Promise.reject('指标不存在');
                }
            })
            .then(indicator => {
                const keys = indicator.type === MANUAL_UPDATE_INDICATOR ? indicator.fieldList : Object.keys(indicator.data[0]);
                const columns = [
                    {
                        title: 'date',
                        dataIndex: 'date',
                        fixed: 'left',
                        width: 150,
                        render: (text, record, index) => {
                            if (this.isEditing(record)) {
                                return (
                                    <Form.Item name="date" initialValue={moment(text, dateFormat)}>
                                        <DatePicker format={dateFormat} />
                                    </Form.Item>
                                )
                            } else {
                                return text;
                            }
                        }
                    },
                    ...keys.filter(d => d !== 'date')
                        .map((d) => ({
                            title: d,
                            dataIndex: d,
                            render: (text, record, index) => {
                                if (this.isEditing(record)) {
                                    return (
                                        <Form.Item name={d} initialValue={text}>
                                            <InputNumber />
                                        </Form.Item>
                                    )
                                } else {
                                    return text;
                                }
                            }
                        })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        align: 'center',
                        width: 200,
                        render: (text, record, index) => {
                            return this.isEditing(record) ?
                            (<>
                                <Button type="link" onClick={this.save}>保存</Button>
                                <Button type="link">取消</Button>
                            </>) :
                            (<>
                                <Button type="link" onClick={() => this.edit(record._key)}>编辑</Button>
                                <Button type="link">删除</Button>
                            </>);
                        }
                    }
                ];
                if (indicator.data) indicator.data.forEach(d => genKey(d));
                this.setState({
                    data: indicator.data || [],
                    canAdd: indicator.type === MANUAL_UPDATE_INDICATOR,
                    columns: columns
                });
            })
            .catch(e => message.error(e.toString()));
    }

    render() {
        const { canAdd, columns, data } = this.state;
        return (
            <div style={{ padding: 10, width: '100%' }}>
                {canAdd && <Button
                    onClick={this.addRow}
                    type='primary'
                    style={{
                        margin: '16px 0',
                    }}
                >
                    Add a row
                </Button>}
                <Form ref={this.formRef}>
                    <Table
                        // components={{
                        //     body: {
                        //         cell: EditableCell,
                        //     },
                        // }}
                        dataSource={data}
                        columns={columns}
                        scroll={{ x: true }}
                        rowKey='_key'
                        bordered
                    ></Table>
                </Form>
            </div>
        );
    }

}
