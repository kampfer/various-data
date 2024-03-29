import { createStore, applyMiddleware } from 'redux'
import thunkMiddleware from 'redux-thunk'
import rootReducer from "./reducers/index.js";

export default createStore(rootReducer, undefined, applyMiddleware(thunkMiddleware));
