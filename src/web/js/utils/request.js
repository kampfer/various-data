export function post(url, data) {
    return fetch(url, {
            body: JSON.stringify(data),
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(json => {
            if (json.code === 200) return json;
            return Promise.reject(json.msg);
        });
}