import React from 'react';
import { List, Card } from 'antd';
import VirtualList from 'rc-virtual-list';
import { connect } from "react-redux";

import { getNews, toggleNews } from '../../store/actions.js';

import 'antd/dist/antd.css';
import styles from './index.module.scss';

class App extends React.Component {

    componentDidMount() {
        this.props.getNews();
    }

    render() {
        const { news, toggleNews } = this.props;
        return (
            <List split={false}>
                <VirtualList
                    data={news}
                    height={window.innerHeight}
                    itemHeight={47}
                    // itemKey='date'
                >
                    {(item, index) => (
                        <List.Item key={index} style={{ padding: 0 }}>
                            <a className={styles.eventCard}>
                                <div className={styles.eventTopArrow}>
                                    <div className={styles.eventTitle}>
                                        <img src="https://finance.sina.com.cn/favicon.ico" alt="" className={styles.eventIcon} />
                                        <div className={styles.eventCategory}>PRODUCT&nbsp;HUNT</div>
                                    </div>
                                    <div className={styles.eventDate}>{item.date}</div>
                                    <div className={styles.timelineDot}>
                                        <div className={styles.timeline}>
                                            <div className={styles.timelineDot}></div>
                                        </div>
                                    </div>
                                </div>
                                <div className={styles.eventContent}>
                                    <h4>#1 Product of the day</h4>
                                    <div> Over 1000 upvotes in 48 hours!?</div>
                                </div>
                                <div className={styles.verticalTimeline}></div>
                            </a>
                        </List.Item>
                    )}
                </VirtualList>
            </List>
        );
    }
}

const mapStateToProps = state => {
    return { news: state.news };
};

export default connect(mapStateToProps, { getNews, toggleNews })(App);
