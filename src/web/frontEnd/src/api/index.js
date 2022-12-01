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
    return fetch(`/stock/${code}`)
        .then(res => res.json())
        .then(res => JSON.parse(res));
}

export function fetchCrawlers() {
    return fetch(`/api/getCrawlers`)
        .then(res => res.json());
}
