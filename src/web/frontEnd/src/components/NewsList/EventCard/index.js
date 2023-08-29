import React from 'react';
import { FlagFilled, FlagOutlined, ZoomInOutlined } from '@ant-design/icons';
import styles from './index.module.scss';
import { pinEvent, unpinEvent } from '../../../store/actions.js';
import { connect } from 'react-redux';
import { Modal } from 'antd';

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

  showDetail = () => {
    const content = this.highLightContent();
    Modal.info({ title: '新闻全文', content });
  };

  highLightContent() {
    const { data, filterWords } = this.props;
    const content = (
      <p
        key={filterWords}
        dangerouslySetInnerHTML={{
          __html: data.rich_text.replaceAll(
            filterWords ? filterWords : null,
            `<font style="background-color: yellow;">${filterWords}</font>`
          ),
        }}
      ></p>
    );
    return content;
  }

  render() {
    const { data } = this.props;
    const tooLong = data.rich_text.length > 100;
    const content = this.highLightContent();
    return (
      <div className={styles.eventCard}>
        <div className={styles.eventCreateTime}>{data.create_time}</div>
        <div className={styles.eventContent}>{content}</div>
        <div className={styles.funcContainer}>
          {tooLong && (
            <ZoomInOutlined className={styles.func} onClick={this.showDetail} />
          )}
          {data.pinned ? (
            <FlagFilled
              onClick={this.unpin}
              className={styles.func}
              style={{ color: 'red' }}
            />
          ) : (
            <FlagOutlined onClick={this.pin} className={styles.func} />
          )}
        </div>
      </div>
    );
  }
}

export default connect(null, { pinEvent, unpinEvent })(EventCard);
