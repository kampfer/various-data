export function fetchNews() {
    return new Promise((resolve, reject) => {
        resolve(
            Array.from({ length : 10000 })
                .map((d, i) => ({
                    author: 'liaowei',
                    title: `测试新闻${i}`,
                    date: Date.now() + i,
                    checked: false
                }))
        )
    });
}