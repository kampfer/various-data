import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { getCrawlers, callCrawler } from '../store/actions.js';
import { Table, message } from 'antd';
import dayjs from 'dayjs';

export default function CrawlersAdmin() {
  const dispatch = useDispatch();
  const crawlers = useSelector(state => state.crawlers.list);

  const update = (moduleName, crawlerName) => {
    dispatch(callCrawler(moduleName, crawlerName));
  };

  useEffect(() => {
    dispatch(getCrawlers());
  }, []);

  const fetchingCrawlers = useSelector(state => state.crawlers.fetchingCrawlers);
  const exeingCrawler = useSelector(state => state.crawlers.exeingCrawler);
  useEffect(() => {
    if (fetchingCrawlers || exeingCrawler) {
      message.loading('Loading...');
    } else {
      message.destroy();
    }
  }, [fetchingCrawlers, exeingCrawler]);

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
          title: '备注',
          dataIndex: 'note',
          render: (_, record) => record.note || '-'
        },
        {
          title: '更新时间',
          dataIndex: 'updateTime',
          render: (_, record) => dayjs(record.updateTime).format('YYYY-MM-DD HH:MM:SS')
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