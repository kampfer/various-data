import React from 'react';
import VirtualList from 'rc-virtual-list';
import { connect } from 'react-redux';
import EventCard from './EventCard/index.js';
import { getNews, setFilters } from '../../store/actions.js';
import dayjs from 'dayjs';
import { Input, DatePicker, Select, Form, Button, Space } from 'antd';

import 'antd/dist/antd.css';
import styles from './index.module.scss';

const { RangePicker } = DatePicker;

class App extends React.Component {
  constructor(props) {
    super(props);
    this.formRef = React.createRef();
  }

  onReset = () => {
    this.formRef.current?.resetFields();
  };

  onFinish = (values) => {
    this.props.setFilters(values);
  };

  componentDidMount() {
    this.props.getNews();
  }

  componentDidUpdate() {
    const { filterWords, sortBy, priority, period } = this.props;
    this.formRef.current?.setFieldsValue({
      filterWords,
      period: period.map((d) => dayjs(d)),
      priority,
      sortBy,
    });
  }

  render() {
    const { news, filterWords } = this.props;
    return (
      <>
        <Form
          labelCol={{ span: 6 }}
          onFinish={this.onFinish}
          ref={this.formRef}
          initialValues={{
            filterWords: '',
            period: [],
            priority: 0,
            sortBy: 0,
          }}
        >
          <Form.Item name="filterWords">
            <Input placeholder="搜索" />
          </Form.Item>
          <Form.Item name="period">
            <RangePicker
              showTime={{
                format: 'HH:mm',
              }}
              format="YYYY-MM-DD HH:mm"
              size="middle"
            />
          </Form.Item>
          <Form.Item label="重要性" name="priority">
            <Select
              options={[
                { value: 0, label: '全部' },
                { value: 1, label: '重要' },
                { value: 2, label: '不重要' },
              ]}
            />
          </Form.Item>
          <Form.Item label="排序" name="sortBy">
            <Select
              options={[
                { value: 0, label: '按时间降序' },
                { value: 1, label: '按时间升序' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space wrap>
              <Button
                type="primary"
                htmlType="submit"
                className="login-form-button"
              >
                确定
              </Button>
              <Button className="login-form-button" onClick={this.onReset}>
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>
        <div className={styles.newsList}>
          {/* <div className={styles.verticalLine}></div> */}
          <div>共{news.length}条</div>
          <VirtualList data={news} height={window.innerHeight} itemHeight={100}>
            {(item, index) => (
              <EventCard key={item.id} data={item} filterWords={filterWords} />
            )}
          </VirtualList>
        </div>
      </>
    );
  }
}

const mapStateToProps = (state) => {
  const { list, filterWords, period, priority, sortBy } = state.news;

  const news = list
    .filter((d) => {
      if (priority === 0) {
        return true;
      } else if (priority === 1) {
        return d.pinned;
      } else if (priority === 2) {
        return !d.pinned;
      }
    })
    .filter((d) => d.rich_text.indexOf(filterWords) > -1)
    .filter((d) => {
      if (period.length === 2) {
        const createTime = dayjs(d.create_time, 'YYYY-MM-DD HH:mm:ss');
        return createTime >= period[0] && createTime <= period[1];
      } else {
        return true;
      }
    })
    .sort((a, b) => {
      const d1 = dayjs(a.create_time, 'YYYY-MM-DD HH:mm:ss');
      const d2 = dayjs(b.create_time, 'YYYY-MM-DD HH:mm:ss');
      if (sortBy === 0) {
        // 降序
        return d1.isAfter(d2) ? -1 : 1;
      } else if (sortBy === 1) {
        // 升序
        return d1.isAfter(d2) ? 1 : -1;
      }
    });

  return {
    news,
    filterWords,
    period,
    priority,
    sortBy,
  };
};

export default connect(mapStateToProps, { getNews, setFilters })(App);
