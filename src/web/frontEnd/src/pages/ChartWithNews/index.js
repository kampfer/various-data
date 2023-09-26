import React from 'react';
import { connect } from 'react-redux';
import KChart from '../../components/KChart/index.js';
import NewsList from '../../components/NewsList/index.js';
import { Input, message } from 'antd';
import { setStockCode } from '../../store/actions.js';

const { Search } = Input;

import './index.css';

class ChartWithNews extends React.Component {
  onSearch = (v) => {
    if (/^sz|sh\d{6}$/.test(v)) {
        this.props.setStockCode(v);
    } else {
        message.error('请输入正确的股票代码');
    }
  };

  componentDidMount() {}

  render() {
    const { code } = this.props;
    return (
      <div id="ChartWithNews">
        <div className="left">
          <NewsList></NewsList>
        </div>
        <div className="right">
          <Search
            addonBefore="股票代码"
            placeholder="请输入股票代码"
            enterButton
            allowClear
            defaultValue={code}
            onSearch={this.onSearch}
            style={{ width: 304 }}
          />
          {/* <div style={{ flex: 1 }}>{code && <KChart code={code}></KChart>}</div> */}
        </div>
      </div>
    );
  }
}

export default connect(
  (state) => ({
    code: state.stock.code,
  }),
  { setStockCode }
)(ChartWithNews);
