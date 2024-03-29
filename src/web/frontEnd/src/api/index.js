import axios from 'axios';
import { message } from 'antd';

function get(...args) {
  return axios.get(...args).then((res) => res.data).then((data) => {
    if (data.code === 200) {
      return data;
    } else {
      message.error(data.msg);
      throw data.msg;
    }
  });
}

export function fetchNews(params = {}) {
  const names = [
    'page',
    'pageSize',
    'filterWords',
    'startTime',
    'endTime',
    'priority',
    'sortBy',
    'category',
  ];
  const queryStr = Object.entries(params)
    .map((d) => (names.includes(d[0]) && d[1] !== undefined ? `${d[0]}=${d[1]}` : ''))
    .filter((d) => !!d)
    .join('&');
  return fetch(`/api/sina7x24/news?${queryStr}`)
    .then((res) => res.json())
    .then((json) => json.data);
}

export function featchTags() {
  return fetch(`/api/sina7x24/tags`)
    .then((res) => res.json())
    .then((json) => json.data);
}

export function fetchStock(code) {
  return fetch(
    `/akshare?funcName=stock_zh_index_daily_em&args=${JSON.stringify({
      symbol: code,
    })}`
  ).then((res) => res.json());
}

export function fetchCrawlers() {
  return fetch(`/api/getCrawlers`).then((res) => res.json());
}

export function exeCrawler(moduleName, crawlerName) {
  return fetch(
    `/api/exeCrawler?funcName=${crawlerName}&moduleName=${moduleName}`
  ).then((res) => res.json());
}

export function pinEvent(id) {
  return fetch(`/api/pinEvent?id=${id}`);
}

export function unpinEvent(id) {
  return fetch(`/api/unpinEvent?id=${id}`);
}

export function createTag(newsId, name) {
  return get(`/api/createTag?name=${name}&newsId=${newsId}`);
}

export function updateTag(id, name) {
  return get(`/api/updateTag?id=${id}&name=${name}`);
}

export function removeTag(id, newsId) {
  return get(`/api/removeTag?tagId=${id}&newsId=${newsId}`);
}
