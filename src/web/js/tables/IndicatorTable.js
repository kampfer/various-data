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
        fetch(`data/${name}.json`)
            .then(response => response.json())
            .then(({ data }) => {
                setColumns([
                    ...Object.keys(data[0]).map((d) => ({ title: d, dataIndex: d })),
                    {
                        title: '操作',
                        dataIndex: 'operation',
                        render: () => 1
                    }
                ]);
                setData(data);
            });

    }, [name]);

    const addRow = () => {};

    return (
        <div style={{ padding: 10 }}>
            <Button
                onClick={addRow}
                type='primary'
                style={{
                    margin: '16px 0',
                }}
            >
                Add a row
            </Button>
            <Table dataSource={data} columns={columns} bordered></Table>
        </div>
    );

}