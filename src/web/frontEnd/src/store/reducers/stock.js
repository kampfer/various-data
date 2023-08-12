import { RECEIVE_STOCK, SELECT_MARK } from '../actionTypes.js';
import moment from 'moment';

export default function (
    state = { zoomStart: moment().subtract(100, 'd'), zoomEnd: moment(),  },
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