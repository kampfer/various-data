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
            indicator: null,
            columns: [],
            data: null,
            canAdd: false,
            editingKey: undefined,
            addingKey: undefined,
        };
        this.formRef = React.createRef();
    }

    addRow = () => {
        const { columns, data } = this.state;
        const { id } = this.props;
        const newData = genKey({});
        columns.forEach(d => {
            if (d.dataIndex !== 'operation') {
                newData[d.dataIndex] = undefined;
            }
        });
        this.setState({
            data: [...data, newData],
            // editingKey: getKey(newData),
            addingKey: getKey(newData)
        });
    }

    save(rowKey) {
        const { data, addingKey, editingKey } = this.state;
        const { id } = this.props;
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
            })
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
        const { indicatorList, id } = this.props;
        const indicator = indicatorList.find(d => d.id === id);
        if (indicator) {
            fetch(`data/${id}.json`)
                .then(response => response.json())
                .then(indicator => {
                    const keys = indicator.type === MANUAL_UPDATE_INDICATOR ? indicator.fieldList : Object.keys(indicator.data[0]);
                    const columns = [
                        {
                            title: 'date',
                            dataIndex: 'date',
                            fixed: 'left',
                            width: 150,
                            render: (text, record, index) => {
                                if (this.isEditing(record) || this.isAdding(record)) {
                                    return (
                                        <Form.Item name="date" initialValue={moment(text)}>
                                            <DatePicker format={dateFormat} />
                                        </Form.Item>
                                    )
                                } else {
                                    return moment(text).format(dateFormat);
                                }
                            }
                        },
                        ...keys.filter(d => d !== 'date')
                            .map((d) => ({
                                title: d,
                                dataIndex: d,
                                render: (text, record, index) => {
                                    if (this.isEditing(record) || this.isAdding(record)) {
                                        return (
                                            <Form.Item name={d} initialValue={text}>
                                                <InputNumber />
                                            </Form.Item>
                                        )
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
                            render: (text, record, index) => {
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
                                        onClick={() => this.delete(id, record.date)}
                                        disabled={addingKey !== undefined || editingKey !== undefined}
                                    >
                                        删除
                                    </Button>
                                </>);
                            }
                        });
                    }
                    if (indicator.data) indicator.data.forEach(d => genKey(d));
                    this.setState({
                        data: indicator.data || [],
                        canAdd: indicator.type === MANUAL_UPDATE_INDICATOR,
                        columns: columns
                    });
                })
        }
    }

    componentDidMount() {
        this.updateData();
    }

    componentDidUpdate(prevProps) {
        const { id } = this.props;
        if (id === prevProps.id && this.state.data) return;
        this.updateData();
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
                        rowKey={KEY_NAME}
                        bordered
                    ></Table>
                </Form>
            </div>
        );
    }

}
