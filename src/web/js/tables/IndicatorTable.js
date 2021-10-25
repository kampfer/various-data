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
import * as request from '../utils/request.js';

const KEY_NAME = '_key';
const genKey = (() => {
    let i = 0;
    return (d) => {
        d[KEY_NAME] = i++;
        return d;
    };
})();

const getKey = (d) => d[KEY_NAME];

const dateFormat = 'YYYY-MM-DD';

export default class IndicatorTable extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            // indicator: null,
            columns: null,
            data: null,
            // canAdd: false,
            editingKey: undefined,
            addingKey: undefined,
        };
        this.formRef = React.createRef();
    }

    addRow = () => {
        const { data } = this.state;
        const { indicator } = this.props;
        const newData = genKey({});
        indicator.fieldList.forEach(key => newData[key] = undefined);
        this.setState({
            data: [...data, newData],
            // editingKey: getKey(newData),
            addingKey: getKey(newData)
        });
    }

    save(rowKey) {
        const { data, addingKey, editingKey } = this.state;
        const id = this.props.indicator.id;
        this.formRef.current.validateFields().then((values) => {
            values.date = values.date.millisecond(0).second(0).minute(0).hour(0).valueOf();
            request.post(
                addingKey !== undefined ? '/api/addIndicatorRow' : '/api/updateIndicatorRow',
                { id, row: values }
            )
                .then(({ code, data: newRow }) => {
                    const newData = [...data];
                    const index = newData.findIndex(d => getKey(d) === rowKey);
                    if (index > -1) {
                        const item = newData[index];
                        newData.splice(index, 1, { ...item, ...newRow });
                    } else {
                        newData.push(genKey(newRow));
                    }
                    this.setState({ data: newData, editingKey: undefined, addingKey: undefined });
                    this.formRef.current.resetFields();
                })
                .catch(e => message.error(e.toString()));
        });
    }

    delete(id, date) {
        fetch(`/api/deleteIndicatorRow?id=${id}&date=${date || ''}`)
            .then(res => res.json())
            .then(json => {
                if (json.code === 200) return json;
                return Promise.reject(json.msg);
            })
            .then(() => {
                const { data } = this.state;
                const newData = [...data];
                const index = newData.findIndex(d => d.date === date);
                if (index > -1) {
                    newData.splice(index, 1);
                    this.setState({ data: newData });
                }
            });
    }

    edit(key) {
        this.setState({ editingKey: key });
    }

    cancel() {
        this.setState({ editingKey: undefined, addingKey: undefined });
        this.formRef.current.resetFields();
    }

    isEditing(record) {
        return getKey(record) === this.state.editingKey;
    }

    isAdding(record) {
        return getKey(record) === this.state.addingKey;
    }

    updateData() {
        const { indicator } = this.props;
        if (indicator) {
            // fetch(`data/${indicator.id}.json`)
            fetch(`api/getIndicator?id=${indicator.id}`)
                .then(response => response.json())
                .then(
                    ({ data }) => {
                        if (data) data.forEach(d => genKey(d));
                        this.setState({ data: data });
                        return indicator.type === MANUAL_UPDATE_INDICATOR ? indicator.fieldList : Object.keys(data[0]);
                    },
                    () => {
                        this.setState({ data: [] });
                        return indicator.fieldList;
                    }
                ).then(keys => {
                    const columns = [
                        {
                            title: 'date',
                            dataIndex: 'date',
                            fixed: 'left',
                            width: 150,
                            render: (text, record) => {
                                if (this.isEditing(record) || this.isAdding(record)) {
                                    return (
                                        <Form.Item name="date" initialValue={moment(text)}>
                                            <DatePicker format={dateFormat} />
                                        </Form.Item>
                                    );
                                } else {
                                    return moment(text).format(dateFormat);
                                }
                            },
                            sorter: (a, b) => a.date - b.date,
                        },
                        ...keys.filter(d => d !== 'date' && d.indexOf('_') < 0)
                            .map((d) => ({
                                title: d,
                                dataIndex: d,
                                render: (text, record) => {
                                    if (this.isEditing(record) || this.isAdding(record)) {
                                        return (
                                            <Form.Item name={d} initialValue={text}>
                                                <InputNumber />
                                            </Form.Item>
                                        );
                                    } else {
                                        return text;
                                    }
                                }
                            }))
                    ];
                    if (indicator.type === MANUAL_UPDATE_INDICATOR) {
                        columns.push({
                            title: '操作',
                            dataIndex: 'operation',
                            align: 'center',
                            width: 200,
                            render: (text, record) => {
                                const { addingKey, editingKey } = this.state;
                                return (this.isEditing(record) || this.isAdding(record)) ?
                                (<>
                                    <Button type="link" onClick={() => this.save(getKey(record))}>保存</Button>
                                    <Button type="link" onClick={() => this.cancel()}>取消</Button>
                                </>) :
                                (<>
                                    <Button
                                        type="link"
                                        onClick={() => this.edit(getKey(record))}
                                        disabled={addingKey !== undefined || editingKey !== undefined}
                                    >
                                        编辑
                                    </Button>
                                    <Button
                                        type="link"
                                        onClick={() => this.delete(indicator.id, record.date)}
                                        disabled={addingKey !== undefined || editingKey !== undefined}
                                    >
                                        删除
                                    </Button>
                                </>);
                            }
                        });
                    }
                    this.setState({ columns: columns });
                });
        }
    }

    componentDidMount() {
        this.updateData();
    }

    // componentDidUpdate(prevProps) {
    //     // const { id } = this.props;
    //     // if (id === prevProps.id && this.state.data) return;
    //     // if (id === prevProps.id) return;
    //     if (this.props.indicator === prevProps.indicator) return;
    //     this.updateData();
    // }

    render() {
        const { columns, data } = this.state;
        const { indicator } = this.props;
        const canAdd = indicator.type === MANUAL_UPDATE_INDICATOR;
        const pageSize = Math.floor((window.innerHeight - 250) / 50);
        return (
            <div style={{ padding: 10, width: '100%' }}>
                <h2>{ indicator.name }</h2>
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
                        rowKey={KEY_NAME}
                        bordered
                        pagination={{ pageSize: pageSize, showTotal: total => `共${total}条` }}
                    ></Table>
                </Form>
            </div>
        );
    }

}
