import React from 'react';
import dayjs from 'dayjs';
import {
  FlagFilled,
  FlagOutlined,
  ZoomInOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import styles from './index.module.scss';
import { pinEvent, unpinEvent } from '../../../store/actions.js';
import { connect } from 'react-redux';
import { Modal, Tag, Input, Tooltip } from 'antd';

class EventCard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      inputVisible: false,
      inputValue: '',
      tags: [],
      editInputIndex: -1,
      editInputValue: '',
    };
    this.inputRef = React.createRef();
    this.editInputRef = React.createRef();
  }

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

  handleInputChange = (e) => {
    this.setState({ inputValue: e.target.value });
  };

  handleInputConfirm = () => {
    const { tags, inputValue } = this.state;
    if (inputValue && !tags.includes(inputValue)) {
      this.setState({ tags: [...tags, inputValue] });
    }
    this.setState({ inputVisible: false, inputValue: '' });
  };

  showInput = () => {
    this.setState({ inputVisible: true });
  };

  handleEditInputChange = (e) => {
    this.setState({ editInputValue: e.target.value });
  };

  handleEditInputConfirm = (e) => {
    const { tags, editInputIndex, editInputValue } = this.state;
    const newTags = [...tags];
    newTags[editInputIndex] = editInputValue;
    this.setState({ tags: newTags, editInputIndex: -1, editInputValue: '' });
  };

  handleClose(removedTag) {
    const { tags } = this.state;
    const newTags = tags.filter((tag) => tag !== removedTag);
    this.setState({ tags: newTags });
  }

  highLightContent() {
    const { data, filterWords } = this.props;
    const content = (
      <p
        key={filterWords}
        dangerouslySetInnerHTML={{
          __html: data.content.replaceAll(
            filterWords ? filterWords : null,
            `<font style="background-color: yellow;">${filterWords}</font>`
          ),
        }}
      ></p>
    );
    return content;
  }

  componentDidUpdate(prevProps, prevState) {
    const { inputVisible, editInputValue } = this.state;
    if (inputVisible !== prevState.inputVisible && inputVisible) {
      this.inputRef.current?.focus();
    }
    if (editInputValue) {
      this.editInputRef.current?.focus();
    }
  }

  render() {
    const { data } = this.props;
    const tooLong = data.content.length > 100;
    const content = this.highLightContent();
    const { inputValue, inputVisible, tags, editInputValue, editInputIndex } =
      this.state;
    return (
      <div className={styles.eventCard}>
        <div className={styles.eventCreateTime}>
          {dayjs(data.createTime).format('YYYY-MM-DD HH:mm:ss')}
        </div>
        <div className={styles.eventContentContainer}>
          <div className={styles.eventContent}>{content}</div>
          <div className={styles.eventTagContainer}>
            {tags.map((tag, index) => {
              if (editInputIndex === index) {
                return (
                  <Input
                    ref={this.editInputRef}
                    key={tag}
                    size="small"
                    style={{
                      width: 64,
                      height: 22,
                      marginInlineEnd: 8,
                      verticalAlign: 'top',
                      marginTop: 5,
                    }}
                    value={editInputValue}
                    onChange={this.handleEditInputChange}
                    onBlur={this.handleEditInputConfirm}
                    onPressEnter={this.handleEditInputConfirm}
                  />
                );
              }
              const isLongTag = tag.length > 20;
              const tagElem = (
                <Tag
                  key={tag}
                  closable
                  color="blue"
                  style={{
                    userSelect: 'none',
                  }}
                  onClose={() => this.handleClose(tag)}
                >
                  <span
                    onDoubleClick={(e) => {
                      if (index !== 0) {
                        this.setState({
                          editInputIndex: index,
                          editInputValue: tag,
                        });
                        e.preventDefault();
                      }
                    }}
                  >
                    {isLongTag ? `${tag.slice(0, 10)}...` : tag}
                  </span>
                </Tag>
              );
              return isLongTag ? (
                <Tooltip title={tag} key={tag}>
                  {tagElem}
                </Tooltip>
              ) : (
                tagElem
              );
            })}
            {inputVisible ? (
              <Input
                ref={this.inputRef}
                type="text"
                size="small"
                style={{
                  width: 64,
                  height: 22,
                  marginInlineEnd: 8,
                  verticalAlign: 'top',
                  marginTop: 5,
                }}
                value={inputValue}
                onChange={this.handleInputChange}
                onBlur={this.handleInputConfirm}
                onPressEnter={this.handleInputConfirm}
              />
            ) : (
              <Tag
                color="blue"
                style={{ borderStyle: 'dashed' }}
                icon={<PlusOutlined />}
                onClick={this.showInput}
              >
                新标签
              </Tag>
            )}
          </div>
        </div>

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
