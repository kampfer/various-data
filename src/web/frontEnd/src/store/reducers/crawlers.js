import { RECEIVE_CRAWLERS } from "../actionTypes.js";

const initialState = [];

export default function(state = initialState, action) {
  switch (action.type) {
    case RECEIVE_CRAWLERS: {
      return action.payload;
    }
    default:
      return state;
  }
}