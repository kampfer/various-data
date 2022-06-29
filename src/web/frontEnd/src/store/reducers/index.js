import { combineReducers } from "redux";
import news from './news.js';
import stock from './stock.js';

export default combineReducers({ news, stock });
