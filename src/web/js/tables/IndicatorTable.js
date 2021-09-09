/* eslint-disable react/prop-types */

import React, { useState, useEffect } from 'react';
import {
    useParams,
} from 'react-router-dom';
import {
    Table,
    Button,
    Form,
    InputNumber,
    DatePicker
} from 'antd';
import moment from 'moment';

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

export default function IndicatorTable() {

    const { name } = useParams();
    const [columns, setColumns] = useState([]);
    const [data, setData] = useState([]);
    const [canAdd, setCanAdd] = useState(false);
    const [editingKey, setEditingKey] = useState('');

    const isEditing = (record) => record.key === editingKey;

    useEffect(() => {
        fetch(`/api/getIndicatorList`)
            .then(res => res.json())
            .then(({ data: indicatorList }) => {
                const indicator = indicatorList.find(d => d.name === name);
                if (!indicator) return;
                if (indicator.type === 1) {
                    return fetch(`data/${name}.json`)
                        .then(response => response.json())
                        .then(({ data }) => {
                            setColumns([
                                {
                                    title: 'date',
                                    dataIndex: 'date',
                                    fixed: 'left',
                                    editable: true,
                                },
                                ...Object.keys(data[0]).filter(d => d !== 'date').map((d) => ({ title: d, dataIndex: d, editable: true })),
                                {
                                    title: '操作',
                                    dataIndex: 'operation',
                                    editable: false,
                                    render: () => 1
                                }
                            ]);
                            setData(data);
                        });
                } else if (indicator.type === 0) {
                    setColumns([{
                        title: 'date',
                        dataIndex: 'date',
                        fixed: 'left',
                        editable: true,
                    },
                    ...indicator.keyList.split(',').filter(d => d !== 'date').map((d) => ({ title: d, dataIndex: d, editable: true })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        render: () => 1
                    }]);
                    setCanAdd(true);
                }
            });
    }, [name]);

    const addRow = () => {
        const newData = {};
        columns.forEach(d => {
            if (d.dataIndex === 'date') {
                newData.date = moment().format('YYYY-MM-DD');
            } else if (d.dataIndex !== 'operation') {
                newData[d.dataIndex] = null;
            }
        });
        setData([...data, newData]);
    };

    const mergedColumns = columns.map((col) => {
        if (!col.editable) {
          return col;
        }

        return {
            ...col,
            onCell: (record) => ({
                record,
                // inputType: col.dataIndex === 'age' ? 'number' : 'text',
                dataIndex: col.dataIndex,
                title: col.title,
                editing: isEditing(record),
            } && console.log(record)),
        };
    });

    return (
        <div style={{ padding: 10, width: '100%' }}>
            {canAdd && <Button
                onClick={addRow}
                type='primary'
                style={{
                    margin: '16px 0',
                }}
            >
                Add a row
            </Button>}
            <Table 
                components={{
                    body: {
                        cell: EditableCell,
                    },
                }}
                dataSource={data}
                columns={mergedColumns}
                scroll={{ x: true }}
                rowKey='date'
                bordered
            ></Table>
        </div>
    );

}