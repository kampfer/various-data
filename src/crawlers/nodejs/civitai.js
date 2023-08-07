import axios from "axios";
import { DATA_PATH } from './constants.js';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

async function main() {
  const dataFile = join(DATA_PATH, 'civitai_images.json');
  let url = `https://civitai.com/api/v1/images?period=AllTime&sort=Most Reactions`;
  // let url = 'https://civitai.com/api/v1/images?cursor=9453&period=AllTime&sort=Most%20Reactions';
  while(url) {
    console.log(`抓取${url}`)
    let data;
    try {
      const res = await axios.get(url);
      data = res.data;
    } catch(e) {
      console.log(e);
      continue;
    }
    const { items, metadata } = data;
    const hasOldData = existsSync(dataFile);
    if (hasOldData) {
      const oldData = readFileSync(dataFile);
      const oldList = JSON.parse(oldData);
      const newList = oldList.concat(items);
      writeFileSync(dataFile, JSON.stringify(newList));
    } else {
      writeFileSync(dataFile, JSON.stringify(items));
    }
    url = metadata.nextPage;
  }
}

main()