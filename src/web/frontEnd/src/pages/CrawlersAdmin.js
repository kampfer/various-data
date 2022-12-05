import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getCrawlers, callCrawler } from '../store/actions.js';
import { Table } from 'antd';

export default function CrawlersAdmin() {
  const dispatch = useDispatch();
  const crawlers = useSelector(state => state.crawlers);
  const update = (moduleName, crawlerName) => {
    dispatch(callCrawler(moduleName, crawlerName));
  };

  useEffect(() => {
    console.log('effect');
    dispatch(getCrawlers());
  }, []);

  return (
    <Table
      dataSource={crawlers}
      columns={[
        { 
          title: '名称', 
          dataIndex: 'name',
          render: (_, record) => <a href={record.source} target="_blank">{record.name}</a>
        },
        { 
          title: '操作',
          render: (_, record) => (<a onClick={() => update(record.moduleName, record.crawlerName)}>更新</a>), 
        },
      ]}
    />
  );
}