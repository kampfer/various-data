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

export default function IndicatorTable() {

    const { name } = useParams();
    const [columns, setColumns] = useState([]);
    const [data, setData] = useState([]);
    const [canAdd, setCanAdd] = useState(false);
    const [editingKey, setEditingKey] = useState('');

    const isEditing = (record) => record._key === editingKey;

    useEffect(() => {
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
                            setData(data);
                            return Object.keys(data[0]);
                        });
                } else if (indicator.type === 0) {
                    setCanAdd(true);
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
                        render: (text, record, index) => {
                            console.log(record, editingKey);
                            return isEditing(record) ? <DatePicker /> : text;
                        }
                    },
                    ...keys.filter(d => d !== 'date')
                        .map((d) => ({
                            title: d,
                            dataIndex: d,
                            editable: true,
                            render: (text, record, index) => <span>{index}</span>
                        })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        editable: false,
                        render: (text, record, index) => 1
                    }
                ];
                setColumns(columns);
            });
    }, [name]);

    const addRow = () => {
        const newData = {};
        genKey(newData);
        columns.forEach(d => {
            if (d.dataIndex === 'date') {
                newData.date = moment().format('YYYY-MM-DD');
            } else if (d.dataIndex !== 'operation') {
                newData[d.dataIndex] = null;
            }
        });
        setData([...data, newData]);
        setEditingKey(newData._key);
    };

    const mergedColumns = columns.map((col) => {
        if (!col.editable) {
          return col;
        }

        return {
            ...col,
            onCell: (record, rowIndex) => ({
                record,
                // inputType: col.dataIndex === 'age' ? 'number' : 'text',
                dataIndex: col.dataIndex,
                title: col.title,
                editing: isEditing(record),
            } && console.log(record, rowIndex)),
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