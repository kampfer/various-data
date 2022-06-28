import { FETCHING_NEWS, RECEIVE_NEWS, TOGGLE_NEWS } from "./actionTypes.js";
import { fetchNews } from '../api/index.js';

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
