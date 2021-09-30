import { ROOT_PATH, DATA_STORE_PATH } from './constants/path.js';

export default class IndicatorManager {

    constructor({ storePath = DATA_STORE_PATH }) {
        this._storePath = storePath;
        this._indicatorList = [];
        this._dataMap = {};
    }

    addIndicator() {}

    deleteIndicator() {}

    grabIndicator() {}

    editIndicator() {}

    getIndicatorList() {}

    addIndicatorRow() {}

    deleteIndicatorRow() {}

    updateIndicatorRow() {}

}