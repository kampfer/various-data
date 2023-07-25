export function fetchNews() {
    return new Promise((resolve, reject) => {
        resolve(
            Array.from({ length : 10 })
                .map((d, i) => ({
                    author: 'liaowei',
                    title: `测试新闻${i}`,
                    date: `2022-04-01`,
                    checked: false
                }))
        )
    });
}

export function fetchStock(code) {
    return fetch(`/akshare/stock_zh_index_daily?symbol=${code}`)
        .then(res => res.json())
        .then(res => JSON.parse(res));
}

export function fetchCrawlers() {
    return fetch(`/api/getCrawlers`)
        .then(res => res.json());
}

export function exeCrawler(moduleName, crawlerName) {
    return fetch(`/api/exeCrawler?funcName=${crawlerName}&moduleName=${moduleName}`)
        .then(res => res.json());
}
