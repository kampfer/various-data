import { FETCHING_NEWS, RECEIVE_NEWS, TOGGLE_NEWS } from "../actionTypes.js";

const initialState = [];

export default function(state = initialState, action) {
    switch (action.type) {
        case RECEIVE_NEWS: {
            return action.payload.news;
        }
        case TOGGLE_NEWS: {
            const { index } = action.payload;
            return state.map((d, i) => {
                if (i === index) d.checked = !d.checked;
                return d;
            });
        }
        default:
            return state;
    }
}
