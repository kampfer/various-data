import {
  RECEIVE_NEWS,
  APPEND_NEWS,
  PIN_EVENT_SUCCESS,
  UNPIN_EVENT_SUCCESS,
  SET_FILTERS,
  RECEIVE_TAGS,
  CREATE_TAG_SUCCESS,
  REMOVE_TAG_SUCCESS,
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
    case CREATE_TAG_SUCCESS: {
      return {
        ...state,
        categories: [
          ...state.categories,
          {
            id: action.payload.tagId,
            name: action.payload.tagName,
            isSinaTag: false,
          },
        ],
        list: state.list.map((d) => {
          if (d.id === action.payload.newsId) {
            return {
              ...d,
              tags: [...d.tags, action.payload.tagId],
            };
          }
          return d;
        }),
      };
    }
    case REMOVE_TAG_SUCCESS: {
      return {
        ...state,
        list: state.list.filter((d) => d !== action.payload.tagId),
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
          return { ...d, significance: d.id === id ? 1 : d.significance };
        }),
      };
    }
    case UNPIN_EVENT_SUCCESS: {
      const id = action.payload;
      return {
        ...state,
        list: state.list.map((d) => {
          return { ...d, significance: d.id === id ? 0 : d.significance };
        }),
      };
    }
    default:
      return state;
  }
}
