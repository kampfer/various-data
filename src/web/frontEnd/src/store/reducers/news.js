import {
  RECEIVE_NEWS,
  APPEND_NEWS,
  PIN_EVENT_SUCCESS,
  UNPIN_EVENT_SUCCESS,
  SET_FILTERS,
  RECEIVE_TAGS,
} from '../actionTypes.js';

const initialState = {
  list: [],
  total: 0,
  filters: {
    filterWords: '',
    period: [],
    priority: 0,
    sortBy: 0,
    category: 0,
  },
  categories: [],
};

export default function (state = initialState, action) {
  switch (action.type) {
    case RECEIVE_NEWS: {
      const { list, total } = action.payload;
      return {
        ...state,
        total,
        list,
      };
    }
    case APPEND_NEWS: {
      const { list, total } = action.payload;
      return {
        ...state,
        total,
        list: state.list.concat(list),
      };
    }
    case RECEIVE_TAGS: {
      return {
        ...state,
        categories: action.payload,
      };
    }
    // case SET_NEWS_PERIOD: {
    case SET_FILTERS: {
      return {
        ...state,
        filters: { ...action.payload },
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
