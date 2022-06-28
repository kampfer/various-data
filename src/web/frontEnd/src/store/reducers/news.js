import { GET_NEWS, TOGGLE_NEWS } from "../actionTypes.js";

const initialState = [];

export default function(state = initialState, action) {
    switch (action.type) {
        case GET_NEWS: {
            return Array.from({ length : 10000 })
                .map((d, i) => ({
                    author: 'liaowei',
                    title: `测试新闻${i}`,
                    date: Date.now() + i,
                    checked: false
                }));
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
