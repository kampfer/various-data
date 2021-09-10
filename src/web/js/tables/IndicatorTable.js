/* eslint-disable react/prop-types */

import React from 'react';
import {
    Table,
    Button,
    Form,
    InputNumber,
    DatePicker,
    Empty
} from 'antd';
import moment from 'moment';

const genKey = (() => {
    let i = 0;
    return (d) => {
        d._key = i++;
        return d;
    };
})();

const EditableCell = ({
    editing,
    dataIndex,
    title,
    // inputType,
    // record,
    // index,
    children,
    ...restProps
}) => {
    const inputNode = dataIndex === 'date' ? <DatePicker /> : <InputNumber />;
    return (
      <td {...restProps}>
        {editing ? (
          <Form.Item
            name={dataIndex}
            style={{
              margin: 0,
            }}
            rules={[
              {
                required: true,
                message: `Please Input ${title}!`,
              },
            ]}
          >
            {inputNode}
          </Form.Item>
        ) : (
          children
        )}
      </td>
    );
};

export default class IndicatorTable extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            indicator: null,
            colums: [],
            data: [],
            canAdd: false,
            editingKey: '',
        };
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

    isEditing(record) {
        return record._key === this.state.editingKey;
    }

    componentDidMount() {
        const { name } = this.props.match.params;
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data: indicatorList }) => indicatorList.find(d => d.name === name))
            .then((indicator) => {
                if (!indicator) return [];
                if (indicator.type === 1) {
                    return fetch(`data/${name}.json`)
                        .then(response => response.json())
                        .then(({ data }) => {
                            data.forEach(d => genKey(d));
                            this.setState({ data })
                            return Object.keys(data[0]);
                        });
                } else if (indicator.type === 0) {
                    this.setState({ canAdd: true })
                    return indicator.keyList.split(',');
                }
            })
            .then((keys) => {
                const columns = [
                    {
                        title: 'date',
                        dataIndex: 'date',
                        fixed: 'left',
                        editable: true,
                        render: (text, record, index) => this.isEditing(record) ? <DatePicker /> : text
                    },
                    ...keys.filter(d => d !== 'date')
                        .map((d) => ({
                            title: d,
                            dataIndex: d,
                            editable: true,
                            render: (text, record, index) => this.isEditing(record) ? <InputNumber /> : text
                        })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        editable: false,
                        render: (text, record, index) => {
                            return this.isEditing(record) ?
                            (<><a>保存</a><a>取消</a></>) :
                            (<><a>编辑</a><a>删除</a></>);
                        }
                    }
                ];
                this.setState({ columns: columns });
            });
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
                <Form>
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
