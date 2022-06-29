import { FETCHING_NEWS, RECEIVE_NEWS, TOGGLE_NEWS, FETCHING_STOCK, RECEIVE_STOCK } from "./actionTypes.js";
import { fetchNews, fetchStock } from '../api/index.js';
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
        dispatch(receiveNews(json));
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
            dates: json.index.map(d => moment(d).format('YYYY-MM-DD')),
            // open close low high
            values: json.data.map(d => [d[0], d[3], d[2], d[1]]),
            volumes: json.data.map((d, i) => [i, d[4], d[0] > d[3] ? 1 : -1]),
            changes
        }
    }
}
