import React, { useEffect } from 'react';
import {
    useParams,
} from 'react-router-dom';
import { Table } from 'antd';

export default function IndicatorTable() {

    const { name } = useParams();

    const columns = [];

    useEffect(() => {
        const { data } = fetch('data/ticketPutAndBackStatByMonth.json').then(response => response.json());
    });

    return (<Table></Table>);

}