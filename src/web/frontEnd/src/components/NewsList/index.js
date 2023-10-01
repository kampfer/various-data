import React from 'react';
import VirtualList from 'rc-virtual-list';
import { connect } from 'react-redux';
import EventCard from './EventCard/index.js';
import { getNews, setFilters, getTags } from '../../store/actions.js';
import dayjs from 'dayjs';
import { Input, DatePicker, Select, Form, Button, Space, Col, Row } from 'antd';
import { ReloadOutlined, FilterOutlined } from '@ant-design/icons';

// import 'antd/dist/antd.css';
import styles from './index.module.scss';

const { RangePicker } = DatePicker;

const initialValues = {
  filterWords: '',
  period: [],
  priority: 0,
  sortBy: 0,
  category: 0,
};

const containerHeight = window.innerHeight - 40 - 10 * 2;

class App extends React.Component {
  constructor(props) {
    super(props);
    this.formRef = React.createRef();
    this.state = { showFitlerPanel: false, curPage: 0, pageSize: 20 };
  }

  onReset = () => {
    this.formRef.current?.resetFields();
    this.props.setFilters(initialValues);
    this.setState({ showFitlerPanel: false });
  };

  onFinish = (values) => {
    this.props.setFilters(values);
    this.setState({ showFitlerPanel: false });
  };

  handleClickAtReloadBtn = () => {
    this.setState({ curPage: 0 });
  };

  handleClickAtFilterBtn = (e) => {
    e.stopPropagation();
    this.setState({ showFitlerPanel: true });
  };

  handleClickAtOuter = () => {
    this.setState({ showFitlerPanel: false });
  };

  handleScroll = (e) => {
    if (
      e.currentTarget.scrollHeight - e.currentTarget.scrollTop <
      containerHeight + 10
    ) {
      const page = this.state.curPage + 1;
      if (page < this.props.total / this.state.pageSize) {
        this.setState({ curPage: page });
      }
    }
  };

  componentDidMount() {
    const { curPage, pageSize } = this.state;
    this.props.getNews({ page: curPage, pageSize });
    this.props.getTags();
  }

  componentDidUpdate(prevProps, prevState) {
    const { filters, total } = this.props;
    const { curPage, pageSize } = this.state;
    if (filters !== prevProps.filters) {
      const { filterWords, sortBy, priority, period } = filters;
      this.formRef.current?.setFieldsValue({
        filterWords,
        period: period.map((d) => dayjs(d)),
        priority,
        sortBy,
      });
      this.props.getNews({
        page: 0,
        pageSize,
        startTime: period[0]?.valueOf(),
        endTime: period[1]?.valueOf(),
        ...filters,
      });
    } else if (curPage !== prevState.curPage) {
      const { period } = filters;
      this.props.getNews({
        page: curPage,
        pageSize,
        startTime: period[0]?.valueOf(),
        endTime: period[1]?.valueOf(),
        ...filters,
      });
    }
  }

  render() {
    const { news, categories, filters, total } = this.props;
    const { filterWords, period, priority, sortBy, category } = filters;
    const { showFitlerPanel } = this.state;
    const categoryItem = categories.find((d) => d.id == category);
    const info = [];
    if (filterWords) info.push(`关键词: ${filterWords}`);
    if (categoryItem) info.push(`分类: ${categoryItem.name}`);
    if (period && period.length > 0)
      info.push(
        `时间: ${dayjs(period[0]).format('YY-MM-DD HH:mm:ss')}至${dayjs(
          period[1]
        ).format('YY-MM-DD HH:mm:ss')}`
      );
    info.push(`重要性: ${['全部', '重要'][priority]}`);
    info.push(`排序: ${sortBy ? '升序' : '降序'}`);
    return (
      <div className={styles.container}>
        <div
          className={styles.filterContainer}
          style={{
            transform: showFitlerPanel ? 'translateY(0%)' : 'translateY(-100%)',
          }}
        >
          <Form
            labelCol={{ span: 6 }}
            onFinish={this.onFinish}
            ref={this.formRef}
            initialValues={initialValues}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="filterWords">
                  <Input placeholder="搜索" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="period">
                  <RangePicker
                    presets={[
                      {
                        label: '今天',
                        value: [dayjs().startOf('d'), dayjs().endOf('d')],
                      },
                    ]}
                    showTime={{
                      format: 'HH:mm',
                    }}
                    format="YYYY-MM-DD HH:mm"
                    size="middle"
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="重要性" name="priority">
                  <Select
                    options={[
                      { value: 0, label: '全部' },
                      { value: 1, label: '重要' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="排序" name="sortBy">
                  <Select
                    options={[
                      { value: 0, label: '按时间降序' },
                      { value: 1, label: '按时间升序' },
                    ]}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="分类" name="category">
                  <Select
                    options={[{ value: 0, label: '全部' }].concat(categories.map((d) => ({
                      value: d.id,
                      label: d.name,
                    })))}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row justify="center">
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
            </Row>
          </Form>
        </div>
        <div className={styles.newsList} onClick={this.handleClickAtOuter}>
          {/* <div className={styles.verticalLine}></div> */}
          <div className={styles.infoBar}>
            <div className={styles.total}>共{total}条</div>
            <div>{info.join(' ')}</div>
            <div>
              <FilterOutlined
                style={{ fontSize: 16 }}
                onClick={this.handleClickAtFilterBtn}
                className={styles.button}
              />
              <ReloadOutlined
                style={{ fontSize: 16 }}
                onClick={this.handleClickAtReloadBtn}
                className={styles.button}
              />
            </div>
          </div>
          <VirtualList
            data={news}
            height={window.innerHeight - 40 - 10 * 2}
            itemHeight={127}
            itemKey="rich_text"
            onScroll={this.handleScroll}
          >
            {(item, index) => (
              <EventCard data={item} filterWords={filterWords} />
            )}
          </VirtualList>
        </div>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  const { list, categories, filters, total } = state.news;
  return {
    total,
    news: list,
    filters,
    categories,
  };
};

export default connect(mapStateToProps, { getNews, setFilters, getTags })(App);
