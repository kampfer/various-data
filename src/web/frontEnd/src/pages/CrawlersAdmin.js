import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getCrawlers } from '../store/actions.js';
import { Space, Table, Tag } from 'antd';

export default function CrawlersAdmin() {
  const dispatch = useDispatch();

  const crawlers = useSelector(state => state.crawlers);

  useEffect(() => {
    console.log('effect');
    dispatch(getCrawlers());
  }, []);

  return (
    <Table
      dataSource={crawlers}
      columns={[
        { title: '名称', dataIndex: 'name' },
        { title: '描述', dataIndex: 'desc' },
        { title: '操作', dataIndex: '' },
      ]}
    />
  );
}