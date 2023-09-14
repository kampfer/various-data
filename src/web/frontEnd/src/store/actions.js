import {
  FETCHING_NEWS,
  RECEIVE_NEWS,
  TOGGLE_NEWS,
  FETCHING_STOCK,
  RECEIVE_STOCK,
  FETCHING_CRAWLERS,
  RECEIVE_CRAWLERS,
  EXEING_CRAWLER,
  EXE_CRAWLER_SUCCESS,
  EXE_CRAWLER_FAIL,
  PIN_EVENT_SUCCESS,
  PIN_EVENT_FAIL,
  UNPIN_EVENT_SUCCESS,
  UNPIN_EVENT_FAIL,
  SET_FILTERS,
  SELECT_MARK,
  SET_STOCK_CODE,
} from './actionTypes.js';
import {
  fetchNews,
  fetchStock,
  fetchCrawlers,
  exeCrawler,
  pinEvent as pinEventById,
  unpinEvent as unpinEventById,
} from '../api/index.js';
import dayjs from 'dayjs';

function fetchingNews() {
  return {
    type: FETCHING_NEWS,
  };
}

function receiveNews(news) {
  return {
    type: RECEIVE_NEWS,
    payload: news,
  };
}

export const getNews = (filters) => (dispatch) => {
  dispatch(fetchingNews());
  return fetchNews().then((list) => {
    dispatch(receiveNews(list));
    dispatch(setFilters(filters));
  });
};

export const toggleNews = (index) => ({
  type: TOGGLE_NEWS,
  payload: {
    index,
  },
});

export const setStockCode = (code) => ({ type: SET_STOCK_CODE, payload: code });

export const getStock = (code) => (dispatch) => {
  dispatch(fetchingStock());
  return fetchStock(code).then((json) => {
    dispatch(receiveStock(json));
  });
};

function fetchingStock() {
  return {
    type: FETCHING_STOCK,
  };
}

function receiveStock(json) {
  const changes = [];
  json.data.forEach((d, i) => {
    if (i === 0) {
      changes.push(0);
    } else {
      changes.push((d[3] - json.data[i - 1][3]) / d[3]);
    }
  });
  return {
    type: RECEIVE_STOCK,
    payload: {
      dates: json.data.map((d) => dayjs(d.date).format('YYYY-MM-DD')),
      // open close low high
      values: json.data.map((d) => [d.open, d.close, d.low, d.high]),
      volumes: json.data.map((d, i) => [
        i,
        d.volume,
        d.close > d.open ? 1 : -1,
      ]),
      changes,
    },
  };
}

export const getCrawlers = () => (dispatch) => {
  dispatch(fetchingCrawlers());
  return fetchCrawlers().then((json) => {
    dispatch(receiveCrawlers(json));
  });
};

function fetchingCrawlers() {
  return {
    type: FETCHING_CRAWLERS,
  };
}

function receiveCrawlers(json) {
  return {
    type: RECEIVE_CRAWLERS,
    payload: json.data,
  };
}

export const callCrawler = (moduleName, crawlerName) => (dispatch) => {
  dispatch(exeingCrawler());
  return exeCrawler(moduleName, crawlerName).then(
    (json) => dispatch(exeCrawlerSuccess(json)),
    (err) => dispatch(exeCrawlerFail(err))
  );
};

function exeingCrawler() {
  return {
    type: EXEING_CRAWLER,
  };
}
function exeCrawlerSuccess() {
  return {
    type: EXE_CRAWLER_SUCCESS,
  };
}
function exeCrawlerFail() {
  return {
    type: EXE_CRAWLER_FAIL,
  };
}

export const pinEvent = (id) => (dispatch) => {
  return pinEventById(id).then(
    () => dispatch(pinEventSuccess(id)),
    () => dispatch(pinEventFail())
  );
};
function pinEventSuccess(id) {
  return {
    type: PIN_EVENT_SUCCESS,
    payload: id
  };
}
function pinEventFail() {
  return {
    type: PIN_EVENT_FAIL,
  };
}

export const unpinEvent = (id) => (dispatch) => {
  return unpinEventById(id).then(
    () => dispatch(unpinEventSuccess(id)),
    () => dispatch(unpinEventFail())
  );
};
function unpinEventSuccess(id) {
  return {
    type: UNPIN_EVENT_SUCCESS,
    payload: id
  };
}
function unpinEventFail() {
  return {
    type: UNPIN_EVENT_FAIL,
  };
}

export const setFilters = (filters) => {
  return {
    type: SET_FILTERS,
    payload: filters
  }
}

export const selectMark = (key) => {
  return {
    type: SELECT_MARK,
    payload: key
  }
}