export function fetchNews() {
    return Promise.all([
        fetch(`/data/sina7x24`),
        fetch(`/data/pinedEvents`)
    ]).then(([res1, res2]) => Promise.all([
        res1.json(),
        res2.json()
    ])).then(([json1, json2]) => {
        const newsList = json1.data;
        const selectedIds = json2.data || [];
        // 去重
        // TODO 很慢
        const list = newsList.reduce((acc, cur) => {
            if (acc.findIndex(d => d.id === cur.id) < 0) {
                acc.push({ pinned: selectedIds.indexOf(cur.id) > -1, ...cur });
            }
            return acc;
        }, []);
        return list;
    });
}

export function fetchStock(code) {
    return fetch(`/akshare?funcName=stock_zh_index_daily_em&args=${JSON.stringify({ symbol: code })}`).then(res => res.json());
}

export function fetchCrawlers() {
    return fetch(`/api/getCrawlers`)
        .then(res => res.json());
}

export function exeCrawler(moduleName, crawlerName) {
    return fetch(`/api/exeCrawler?funcName=${crawlerName}&moduleName=${moduleName}`)
        .then(res => res.json());
}

export function pinEvent(id) {
    return fetch(`/api/pinEvent?id=${id}`);
}

export function unpinEvent(id) {
    return fetch(`/api/unpinEvent?id=${id}`);
}
