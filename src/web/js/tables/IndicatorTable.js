import React, { useState, useEffect } from 'react';
import {
    useParams,
} from 'react-router-dom';
import { Table, Button } from 'antd';

export default function IndicatorTable() {

    const { name } = useParams();
    const [columns, setColumns] = useState([]);
    const [data, setData] = useState([]);

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
                                },
                                ...Object.keys(data[0]).filter(d => d !== 'date').map((d) => ({ title: d, dataIndex: d })),
                                {
                                    title: '操作',
                                    dataIndex: 'operation',
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
                    },
                    ...indicator.keyList.split(',').filter(d => d !== 'date').map((d) => ({ title: d, dataIndex: d })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        render: () => 1
                    }])
                }
            });
    }, [name]);

    const addRow = () => {};

    return (
        <div style={{ padding: 10, width: '100%' }}>
            <Button
                onClick={addRow}
                type='primary'
                style={{
                    margin: '16px 0',
                }}
            >
                Add a row
            </Button>
            <Table dataSource={data} columns={columns} scroll={{ x: true }} rowKey='date' bordered></Table>
        </div>
    );

}