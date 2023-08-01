import { FETCHING_NEWS, RECEIVE_NEWS, TOGGLE_NEWS, FETCHING_STOCK, RECEIVE_STOCK, FETCHING_CRAWLERS, RECEIVE_CRAWLERS, EXEING_CRAWLER, EXE_CRAWLER_SUCCESS, EXE_CRAWLER_FAIL } from "./actionTypes.js";
import { fetchNews, fetchStock, fetchCrawlers, exeCrawler } from '../api/index.js';
import moment from 'moment';

function fetchingNews() {
    return {
        type: FETCHING_NEWS
    };
}

function receiveNews(news) {
    return {
        type: RECEIVE_NEWS,
        payload: {
            news
        }
    };
}

export const getNews = () => (dispatch) => {
    dispatch(fetchingNews());
    return fetchNews().then((json) => {
        dispatch(receiveNews(json.data));
    });
};

export const toggleNews = (index) => ({
    type: TOGGLE_NEWS,
    payload: {
        index
    }
});

export const getStock = (code) => (dispatch) => {
    dispatch(fetchingStock());
    return fetchStock(code).then((json) => {
        dispatch(receiveStock(json));
    });
};

function fetchingStock() {
    return {
        type: FETCHING_STOCK
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
            dates: json.data.map(d => moment(d.date).format('YYYY-MM-DD')),
            // open close low high
            values: json.data.map(d => [d.open, d.close, d.low, d.high]),
            volumes: json.data.map((d, i) => [i, d.volume, d.close > d.open ? 1 : -1]),
            changes
        }
    }
}

export const getCrawlers = () => (dispatch) => {
    dispatch(fetchingCrawlers());
    return fetchCrawlers().then((json) => {
        dispatch(receiveCrawlers(json));
    });
}

function fetchingCrawlers() {
    return {
        type: FETCHING_CRAWLERS
    };
}

function receiveCrawlers(json) {
    return {
        type: RECEIVE_CRAWLERS,
        payload: json.data
    }
}

export const callCrawler = (moduleName, crawlerName) => (dispatch) => {
    dispatch(exeingCrawler());
    return exeCrawler(moduleName, crawlerName).then(
        json => dispatch(exeCrawlerSuccess(json)),
        err => dispatch(exeCrawlerFail(err))
    );
}

function exeingCrawler() {
    return {
        type: EXEING_CRAWLER
    };
}
function exeCrawlerSuccess() {
    return {
        type: EXE_CRAWLER_SUCCESS
    };
}
function exeCrawlerFail() {
    return {
        type: EXE_CRAWLER_FAIL
    };
}
