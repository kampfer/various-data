import { DATA_STORE_PATH } from "./constants/path.js";
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import * as crawlers from './crawlers/index.js';

export default class IndicatorManager {

    constructor({
        storePath = DATA_STORE_PATH,
    }) {
        this._indicatorListPath = path.join(storePath, 'indicators.json');
        this._indicatorList = this.readIndicatorList() || [];
    }

    readFile(path) {
        let data = null;
        try {
            data = JSON.parse(fs.readFileSync(path));
        } catch(e) {
            console.log(e);
        }
        return data;
    }

    writeFile(path, data) {
        // fs.writeFileSync(path, JSON.stringify(data, null, 4));   // 带换行
        fs.writeFileSync(path, JSON.stringify(data));
    }

    readIndicatorList() {
        return this.readFile(this._indicatorListPath);
    }

    getIndicatorList() {
        return this._indicatorList;
    }

    getIndicator(id) {
        return this._indicatorList.find(d => d.id === id);
    }

    addIndicator({ name, description, graph, fieldList, crawler, type }) {
        const indicatorId = uuidv4();
        const now = Date.now();
        const newIndicator = {
            name,
            description,
            graph,
            crawler,
            type,
            fieldList: fieldList ? ['date', ...fieldList.split(',')] : null,
            id: indicatorId,
            data: [],
            dataPath: path.join(DATA_STORE_PATH, `${indicatorId}.json`),
            createTime: now,
            updateTime: now,
        };
        this._indicatorList.push(newIndicator);
        return newIndicator;
    }

    deleteIndicator(id) {
        const index = this._indicatorList.findIndex(d => d.id === id);
        if (index > -1) {
            return this._indicatorList.splice(index, 1);
        }
    }

    updateIndicator(id, { name, description, graph, fieldList, crawler, type, updateTime }) {
        let indicator = this.getIndicator(id);
        Object.assign(indicator, { name, description, graph, fieldList, crawler, type, updateTime });
        return indicator;
    }

    async crawlIndicator(id) {
        const indicator = this.getIndicator(id);
        let crawler = crawlers[indicator.crawler];
        if (crawler) {
            const data = await crawler();
            this.writeFile(indicator.dataPath, data);
            return data;
        }
    }

}