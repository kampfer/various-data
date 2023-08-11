import axios from "axios";
import { DATA_PATH } from './constants.js';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join, extname } from 'path';

async function loopImageList() {
  const dataFile = join(DATA_PATH, 'civitai/images.json');
  const recordFilePath = join(DATA_PATH, 'civitai/nextPage');
  let url = `https://civitai.com/api/v1/images?period=AllTime&sort=Most Reactions`;
  if (existsSync(recordFilePath)) {
    url = readFileSync(recordFilePath);
  }
  while(url) {
    writeFileSync(recordFilePath, `${url}`);

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

async function _loop(idx, list) {
  const tmpFilePath = join(DATA_PATH, 'civitai', 'idx');
  writeFileSync(tmpFilePath, `${idx}`);

  const item = list[idx];
  const url = item.url;
  const imageExtname = extname(url);
  console.log(`抓取[${idx + 1}/${list.length}]  id: ${item.id}  url: ${url}`);
  const res = await axios.get(url, { responseType: 'arraybuffer' });
  writeFileSync(join(DATA_PATH, 'civitai', `${item.id}${imageExtname}`), res.data);
}

async function loopImages() {
  const tmpFile = join(DATA_PATH, 'civitai', 'idx');
  const dataFile = join(DATA_PATH, 'civitai_images.json');
  if (existsSync(dataFile)) {
    let start = 0;
    if (existsSync(tmpFile)) {
      const idx = Number(readFileSync(tmpFile));
      start = idx;
    }
    const listContent = readFileSync(dataFile);
    const list = JSON.parse(listContent);
    while (start < list.length) {
      try {
        await _loop(start, list);
        start++;
      } catch(e) {
        console.log('error and restart');
        continue;
      }
    }
  }
}

async function main() {
  // loopImageList();
  loopImages();
}

main()