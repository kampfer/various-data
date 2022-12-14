import { FETCHING_CRAWLERS, RECEIVE_CRAWLERS, EXEING_CRAWLER, EXE_CRAWLER_SUCCESS, EXE_CRAWLER_FAIL } from "../actionTypes.js";

const initialState = {
  list: [],
  fetchingCrawlers: false,
  exeingCrawler: false,
};

export default function(state = initialState, action) {
  switch (action.type) {
    case RECEIVE_CRAWLERS: {
      action.payload.forEach((d, i) => d.key = i);
      return {
        fetchingCrawlers: false,
        list: action.payload
      };
    }
    case FETCHING_CRAWLERS: {
      return {
        ...state,
        fetchingCrawlers: true
      };
    }
    case EXEING_CRAWLER: {
      return {
        ...state,
        exeingCrawler: true
      }; 
    }
    case EXE_CRAWLER_SUCCESS:
    case EXE_CRAWLER_FAIL: {
      return {
        ...state,
        exeingCrawler: false
      }; 
    }
    default:
      return state;
  }
}