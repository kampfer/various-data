import React from 'react';
import VirtualList from 'rc-virtual-list';
import { connect } from 'react-redux';
import EventCard from './EventCard/index.js';
import { getNews, setFilters } from '../../store/actions.js';
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

class App extends React.Component {
  constructor(props) {
    super(props);
    this.formRef = React.createRef();
    this.state = { showFitlerPanel: false };
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
    this.props.getNews();
  };

  handleClickAtFilterBtn = (e) => {
    e.stopPropagation();
    this.setState({ showFitlerPanel: true });
  };

  handleClickAtOuter = () => {
    this.setState({ showFitlerPanel: false });
  }

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
    const {
      news,
      filterWords,
      categories,
      period,
      priority,
      sortBy,
      category,
    } = this.props;
    const { showFitlerPanel } = this.state;
    const categoryItem = categories.find(d => d.id == category);
    const info = [];
    if (filterWords) info.push(`关键词: ${filterWords}`);
    if (categoryItem) info.push(`分类: ${categoryItem.name}`);
    if (period.length > 0) info.push(`时间: ${dayjs(period[0]).format('YY-MM-DD HH:ss')}至${dayjs(period[1]).format('YY-MM-DD HH:ss')}`);
    info.push(`重要性: ${['全部', '重要', '不重要'][priority]}`);
    info.push(`排序: ${sortBy ? '升序': '降序'}`);
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
                      { value: 2, label: '不重要' },
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
                    options={categories.map((d) => ({
                      value: d.id,
                      label: d.name,
                    }))}
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
            <div className={styles.total}>共{news.length}条</div>
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
            itemHeight={118}
            itemKey="rich_text"
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
  const { list, filterWords, period, priority, sortBy, categories, category } =
    state.news;
  console.log(category, categories);
  const news = list
    .filter((d) => {
      return d.tag.reduce(
        (prev, cur) => (category ? cur.id === category || prev : true),
        false
      );
    })
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
    categories,
    category,
  };
};

export default connect(mapStateToProps, { getNews, setFilters })(App);
