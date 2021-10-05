import { DATA_STORE_PATH } from "./constants/path.js";
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import * as crawlers from './crawlers/index.js';
import { MANUAL_UPDATE_INDICATOR } from "./constants/indicatorTypes.js";

function readFile(path) {
    let data = null;
    try {
        data = JSON.parse(fs.readFileSync(path));
    } catch(e) {
        console.log(e);
    }
    return data;
}

function writeFile(path, data, formatted = false) {
    if (formatted) {
        fs.writeFileSync(path, JSON.stringify(data, null, 4));   // 带换行
    } else {
        fs.writeFileSync(path, JSON.stringify(data));
    }
}

class Indicator {

    static props = [
        'id', 'createTime', 'dataPath',
        'name', 'description', 'graph', 'fieldList',
        'crawler', 'type', 'updateTime', 'dataCount',
    ]

    constructor(props, storePath = DATA_STORE_PATH) {
        this.update(props);
        if (this.id === undefined) this.id = uuidv4();
        if (this.createTime === undefined) this.createTime = Date.now();
        if (this.updateTime === undefined) this.updateTime = Date.now();
        if (this.dataPath === undefined) this.dataPath = path.join(storePath, `${this.id}.json`);
    }

    update(props) {
        Indicator.props.forEach(key => {
            if (props[key] !== undefined) this[key] = props[key];
        });
    }

    addRow(props) {
        let meta = readFile(this.dataPath);
        if (!meta) {
            meta = this.toJSON();
            meta.data = [];
        }
        let newRow = {};
        this.fieldList.forEach(key => newRow[key] = props[key]);
        meta.data.push(newRow);
        writeFile(this.dataPath, meta);
        return newRow;
    }

    updateRow(props) {
        const meta = readFile(this.dataPath);
        const index = meta.data.findIndex(d => d.date === props.date);
        if (index > -1) {
            const row = meta.data[index];
            const newRow = { ...row, ...props };
            meta.data.splice(index, 1, { ...row, ...props });
            writeFile(this.dataPath, meta);
            return newRow;
        }
    }

    deleteRow(date) {
        const meta = readFile(this.dataPath);
        const index = meta.data.findIndex(d => d.date === date);
        if (index > -1) {
            meta.data.splice(index, 1);
            writeFile(this.dataPath, meta);
        }
    }

    async crawl() {
        let crawler = crawlers[this.crawler];
        if (crawler) {
            const data = await crawler(this);
            writeFile(this.dataPath, data);
            this.update({ updateTime: Date.now() });
            return data;
        }
    }

    toJSON(readData = false) {
        let data = {
            id: this.id,
            createTime: this.createTime,
            dataPath: this.dataPath,
        };
        Indicator.props.forEach(key => data[key] = this[key]);
        if (readData) data.data = readFile(this.dataPath);
        return data;
    }

}

export default class IndicatorManager {

    constructor({
        storePath = DATA_STORE_PATH,
    }) {
        this._storePath = storePath;
        this._indicatorListPath = path.join(storePath, 'indicators.json');
        this._indicatorList = this.readIndicatorList();
    }

    saveIndicatorList() {
        writeFile(this._indicatorListPath, this.getIndicatorList(), true);
    }

    readIndicatorList() {
        const data = readFile(this._indicatorListPath);
        let list = [];
        if (data) list = data.map(props => new Indicator(props));
        return list;
    }

    getIndicatorList() {
        return this._indicatorList.map(i => i.toJSON());
    }

    getIndicator(id) {
        return this._indicatorList.find(d => d.id === id);
    }

    addIndicator(props) {
        if (props.type === MANUAL_UPDATE_INDICATOR) props.fieldList = props.fieldList.split(',');
        const newIndicator = new Indicator(props);
        this._indicatorList.push(newIndicator);
        this.saveIndicatorList();
        return newIndicator.toJSON();
    }

    deleteIndicator(id) {
        const index = this._indicatorList.findIndex(d => d.id === id);
        if (index > -1) {
            const deletedIndicator = this._indicatorList.splice(index, 1);
            this.saveIndicatorList();
            fs.rmSync(deletedIndicator.dataPath);
            return deletedIndicator;
        }
    }

    async crawlIndicator(id) {
        const indicator = this.getIndicator(id);
        const ret = await indicator.crawl();
        return ret;
    }

}