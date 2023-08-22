import React from 'react';
import { PushpinOutlined, PushpinFilled } from '@ant-design/icons';
import styles from './index.module.scss';
import { pinEvent, unpinEvent } from '../../../store/actions.js';
import { connect } from 'react-redux';

class EventCard extends React.Component {
  pin = () => {
    const { data, pinEvent } = this.props;
    const { id } = data;
    return pinEvent(id);
  };

  unpin = () => {
    const { data, unpinEvent } = this.props;
    const { id } = data;
    return unpinEvent(id);
  };

  render() {
    const { data, filterWords } = this.props;
    return (
      <span className={styles.eventCardWrapper}>
        <a className={styles.eventCard}>
          <div className={styles.eventTopArrow}>
            <div className={styles.eventTitle}>
              {data.pinned ? (
                <PushpinFilled
                  className={styles.eventIcon}
                  onClick={this.unpin}
                />
              ) : (
                <PushpinOutlined
                  className={styles.eventIcon}
                  onClick={this.pin}
                />
              )}
              <div className={styles.eventCategory}>新浪新闻</div>
            </div>
            <div className={styles.eventDate}>{data.create_time}</div>
            <div className={styles.timelineDot}>
              <div className={styles.timeline}>
                <div className={styles.timelineDot}></div>
              </div>
            </div>
          </div>
          <div className={styles.eventContent}>
            {/* <h4>#1 Product of the day</h4> */}
            <div
              dangerouslySetInnerHTML={{
                __html: data.rich_text.replaceAll(
                  filterWords ? filterWords : null,
                  `<font style="background-color: yellow;">${filterWords}</font>`
                ),
              }}
            ></div>
          </div>
          {/* <div className={styles.verticalTimeline}></div> */}
        </a>
      </span>
    );
  }
}

export default connect(null, { pinEvent, unpinEvent })(EventCard);
