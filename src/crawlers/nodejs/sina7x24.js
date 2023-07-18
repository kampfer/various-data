import axios from "axios";
import { DATA_PATH } from './constants.js';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import moment from 'moment';

async function crawlFeed(type = 0, id) {
  const params = {
    callback: `jQuery123`,
    page: 1,
    page_size: 100, // pageSize超过100不生效
    zhibo_id: 152,
    tag_id: 0,
    dire: 'f',
    dpc: 1,
    pagesize: 100,  // pageSize超过100不生效
    id,
    type,  // 0 从最新的news往回取20条；1 从指定id的news往回取20条
    _: Date.now()
  };
  const url = `https://zhibo.sina.com.cn/api/zhibo/feed?${Object.entries(params).map(([k, v]) => `${k}=${v}`).join('&')}`;
  
  console.log(`请求${url}`);
  const { data } = await axios.get(url);
  const jsonStr = data.substring(14, data.length - 14);
  const { result } = JSON.parse(jsonStr);

  if (result.status.code === 0) {
    return result.data;
  }
}

async function crawlLatestFeed() {
  const firstRes = await crawlFeed();
  let minId = firstRes.feed.min_id;
  let totalNum = firstRes.feed.page_info.totalNum;
  let list = firstRes.feed.list;

  while(list.length < totalNum) {
    const res = await crawlFeed(1, minId);
    res.feed.list.forEach(item => list.push(item));
    minId = list[list.length - 1].id;
  }

  return list;
}

function mergeList(old, latest) {
  const minId = latest[latest.length - 1].id;
  const idx = old.findIndex(d => d.id === minId);
  if (idx > -1) {
    const count = latest.length - (idx + 1);
    for(let i = count - 1; i >= 0; i--) {
      old.unshift(latest[i]);
    }
    console.log(`【${moment().utcOffset(8).format('YYYY-MM-DD LTS')}】本次执行已添加${count}条新数据，现有总计${old.length}条数据`)
    return old;
  } else {
    return [...latest, ...old];
  }
}

async function crawlSina7x24() {
  const latestList = await crawlLatestFeed();
  const dataFile = join(DATA_PATH, 'sina7x24.json');
  const hasOldData = existsSync(dataFile);
  if (hasOldData) {
    const oldData = readFileSync(dataFile);
    const oldList = JSON.parse(oldData);
    const newList = mergeList(oldList, latestList);
    writeFileSync(dataFile, JSON.stringify(newList));
  } else {
    writeFileSync(dataFile, JSON.stringify(latestList));
  }
}

function main() {
  const tick = () => {
    try {
      crawlSina7x24();
    } catch(e) {
      console.log(e);
    }
    setTimeout(tick, 60 * 60 * 1000);
  }
  tick();
}

main();
