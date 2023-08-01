export function fetchNews() {
    return fetch(`/data/sina7x24`).then(res => res.json());
}

export function fetchStock(code) {
    return fetch(`/akshare?funcName=stock_zh_index_daily&args=${JSON.stringify({ symbol: code })}`).then(res => res.json());
}

export function fetchCrawlers() {
    return fetch(`/api/getCrawlers`)
        .then(res => res.json());
}

export function exeCrawler(moduleName, crawlerName) {
    return fetch(`/api/exeCrawler?funcName=${crawlerName}&moduleName=${moduleName}`)
        .then(res => res.json());
}
