export function mean(arr) {
    return arr.reduce((acc, cur) => cur + acc) / arr.length;
}

export function geometricMean(arr) {
    return Math.pow(arr.reduce((acc, cur) => cur * acc), 1 / arr.length);
}

export function variance(arr) {
    const avg = mean(arr);
    return arr.reduce((acc, cur) => acc += Math.pow(cur - avg, 2), 0) / (arr.length - 1);
}

export function std(arr) {
    return Math.pow(variance(arr), 1 / 2);
}
