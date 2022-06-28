import { GET_NEWS, TOGGLE_NEWS } from "./actionTypes.js";

export const getNews = () => ({
    type: GET_NEWS
});

export const toggleNews = (index) => ({
    type: TOGGLE_NEWS,
    payload: {
        index
    }
});
