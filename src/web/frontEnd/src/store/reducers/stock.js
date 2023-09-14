import {
  RECEIVE_STOCK,
  SELECT_MARK,
  SET_FILTERS,
  SET_STOCK_CODE,
} from '../actionTypes.js';
import dayjs from 'dayjs';

export default function (
  state = { zoomStart: dayjs().subtract(100, 'd'), zoomEnd: dayjs(), code: 'sh000001' },
  action
) {
  switch (action.type) {
    case SET_STOCK_CODE:
      return {
        ...state,
        code: action.payload,
      };
    case RECEIVE_STOCK:
      return {
        ...state,
        ...action.payload,
      };
    case SELECT_MARK: {
      return {
        ...state,
        selectedMark: action.payload,
      };
    }
    case SET_FILTERS: {
      if (action.payload && state.selectedMark) {
        if (action.payload.length === 0) {
          return {
            ...state,
            selectedMark: null,
          };
        }

        const { period } = action.payload;
        const selectedMark = state.selectedMark;
        const selectedDate = dayjs(selectedMark, 'YYYY-MM-DD');
        if (
          dayjs(period[0]).isBefore(selectedDate, 'day') ||
          dayjs(period[1]).isAfter(selectedDate, 'day')
        ) {
          return {
            ...state,
            selectedMark: null,
          };
        }
      }
    }
    default:
      return state;
  }
}
