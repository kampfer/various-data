import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getCrawlers, callCrawler } from '../store/actions.js';
import { Table, message } from 'antd';

export default function CrawlersAdmin() {
  const dispatch = useDispatch();
  const crawlers = useSelector(state => state.crawlers.list);
  const update = (moduleName, crawlerName) => {
    dispatch(callCrawler(moduleName, crawlerName));
  };

  // const fetchingCrawlers = useSelector(state => state.crawlers.fetchingCrawlers);
  // if (fetchingCrawlers) {
  //   message.loading('Loading...');
  // } else {
  //   message.destroy();
  // }

  // const exeingCrawler = useSelector(state => state.crawlers.exeingCrawler);
  // if (exeingCrawler) {
  //   message.loading('Loading...');
  // } else {
  //   message.destroy();
  // }

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
          title: '更新时间',
          dataIndex: 'updateTime'
        },
        { 
          title: '数据地址',
          dataIndex: 'url',
          render: (_, record) => <a href={record.url} target="_blank">{record.url}</a>
        },
        { 
          title: '操作',
          render: (_, record) => (<a onClick={() => update(record.moduleName, record.crawlerName)}>更新</a>), 
        },
      ]}
    />
  );
}