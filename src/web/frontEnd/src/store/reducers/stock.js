import { RECEIVE_STOCK, SELECT_MARK } from '../actionTypes.js';
import dayjs from 'dayjs';

export default function (
    state = { zoomStart: dayjs().subtract(100, 'd'), zoomEnd: dayjs(),  },
    action
) {
    switch (action.type) {
        case RECEIVE_STOCK:
            return {
                ...state,
                ...action.payload
            };
        case SELECT_MARK: {
            return {
                ...state,
                selectedMark: action.payload
            }
        }
        default:
            return state;
    }
}