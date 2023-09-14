import {
  RECEIVE_NEWS,
  TOGGLE_NEWS,
  PIN_EVENT_SUCCESS,
  UNPIN_EVENT_SUCCESS,
  SET_FILTERS,
} from '../actionTypes.js';

const initialState = {
  list: [],
  filterWords: '',
  period: [],
  priority: 0,
  sortBy: 0,
  category: 0,
  categories: []
};

export default function (state = initialState, action) {
  switch (action.type) {
    case RECEIVE_NEWS: {
      return {
        ...state,
        list: action.payload.list,
        categories: action.payload.categories
      };
    }
    // case SET_NEWS_PERIOD: {
    case SET_FILTERS: {
      return {
        ...state,
        ...action.payload,
      };
    }
    case PIN_EVENT_SUCCESS: {
      const id = action.payload;
      return {
        ...state,
        list: state.list.map((d) => {
          return { ...d, pinned: d.id === id ? true : d.pinned };
        }),
      };
    }
    case UNPIN_EVENT_SUCCESS: {
      const id = action.payload;
      return {
        ...state,
        list: state.list.map((d) => {
          return { ...d, pinned: d.id === id ? false : d.pinned };
        }),
      };
    }
    default:
      return state;
  }
}
