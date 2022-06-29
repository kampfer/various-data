import { RECEIVE_STOCK } from '../actionTypes.js';

export default function (state = {}, action) {
    switch (action.type) {
        case RECEIVE_STOCK:
            return {
                ...action.payload
            };
        default:
            return state;
    }
}