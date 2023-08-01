import { RECEIVE_NEWS, TOGGLE_NEWS, PIN_EVENT_SUCCESS, UNPIN_EVENT_SUCCESS } from "../actionTypes.js";

const initialState = [];

export default function(state = initialState, action) {
    switch (action.type) {
        case RECEIVE_NEWS: {
            return action.payload.news;
        }
        // case TOGGLE_NEWS: {
        //     const { index } = action.payload;
        //     return state.map((d, i) => {
        //         if (i === index) d.pinned = !d.checked;
        //         return d;
        //     });
        // }
        case PIN_EVENT_SUCCESS: {
            const id = action.payload;
            return state.map(d => {
                return { ...d, pinned: d.id === id ? true : d.pinned }
            });
        }
        case UNPIN_EVENT_SUCCESS: {
            const id = action.payload;
            return state.map(d => {
                return { ...d, pinned: d.id === id ? false : d.pinned }
            });
        }
        default:
            return state;
    }
}
