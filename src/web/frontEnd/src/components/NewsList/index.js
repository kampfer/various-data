import React from 'react';
import VirtualList from 'rc-virtual-list';
import { connect } from 'react-redux';
import EventCard from './EventCard/index.js';
import { getNews } from '../../store/actions.js';
import moment from 'moment';

import 'antd/dist/antd.css';
import styles from './index.module.scss';

class App extends React.Component {
  componentDidMount() {
    this.props.getNews();
  }

  render() {
    const { news } = this.props;
    return (
      <div className={styles.newsList}>
        <div className={styles.verticalLine}></div>
        <VirtualList data={news} height={window.innerHeight} itemHeight={100}>
          {(item, index) => <EventCard key={item.id} data={item} />}
        </VirtualList>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  const period = state.news.period;
  const list =
    state.news.period.length === 2
      ? state.news.list.filter((d) => {
          const createTime = moment(d.create_time, 'YYYY-MM-DD HH:mm:ss');
          return createTime >= period[0] && createTime <= period[1] && d.pinned;
        })
      : state.news.list;
  return { news: list };
};

export default connect(mapStateToProps, { getNews })(App);
