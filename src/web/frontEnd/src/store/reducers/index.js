import { combineReducers } from "redux";
import news from './news.js';
import stock from './stock.js';
import crawlers from './crawlers.js';

export default combineReducers({ news, stock, crawlers });
