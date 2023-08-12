import {
  RECEIVE_NEWS,
  TOGGLE_NEWS,
  PIN_EVENT_SUCCESS,
  UNPIN_EVENT_SUCCESS,
  SET_NEWS_PERIOD
} from '../actionTypes.js';

const initialState = {
  list: [],
  period: [],
};

export default function (state = initialState, action) {
  switch (action.type) {
    case RECEIVE_NEWS: {
      return {
        ...state,
        list: action.payload.news,
      };
    }
    case SET_NEWS_PERIOD: {
        debugger;
        return {
            ...state,
            period: [action.payload.start, action.payload.end]
        };
    }
    case PIN_EVENT_SUCCESS: {
      const id = action.payload;
      return state.map((d) => {
        return { ...d, pinned: d.id === id ? true : d.pinned };
      });
    }
    case UNPIN_EVENT_SUCCESS: {
      const id = action.payload;
      return state.map((d) => {
        return { ...d, pinned: d.id === id ? false : d.pinned };
      });
    }
    default:
      return state;
  }
}
