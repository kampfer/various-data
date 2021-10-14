import * as request from '../crawlers/request.js';
import moment from 'moment';
import XLSX from 'xlsx';
import { ROOT_PATH } from '../constants/path.js';
import path from 'path';
import { 
    mean, 
    geometricMean,
    variance,
    std,
} from './statistic.js';

function analyse(arr) {
    console.log(`=======================`);
    console.log(`总收益的算术平均：${mean(arr)}`);
    console.log(`总收益的几何平均：${geometricMean(arr.map(v => 1 + v)) - 1}`);
    console.log(`总收益的标准差：${std(arr)}`);
    console.log(`【总收益】算术平均-1/2方差：${mean(arr) - variance(arr) / 2}`);
    console.log(`=======================`);
}

request.get({
    url: 'http://127.0.0.1:3000/api/getIndicator',
    data: {
        id: '3b065983-7795-40dc-b104-48c072803d33'
    }
})
.then(res => res.json())
.then(({ data }) => {
    let prevValue;
    const arr = [];
    for(let i = 0, l = data.length; i < l; i++) {
        let item = data[i];
        let time = moment(data[i].date);
        if (i === 0) {
            prevValue = parseFloat(item.close, 10);
        } else {
            let nextItem = data[i + 1];
            if (!nextItem || moment(nextItem.date).year() !== time.year()) {
                const end = parseFloat(item.close, 10);
                arr.push({
                    start: prevValue,
                    end: end,
                    r: (end - prevValue) / prevValue
                });
                prevValue = end;
            }
        }
    }
    return arr;
}).then(arr => {
    const xlsxFiles = [
        'data/国债及其他债券收益率曲线/2011年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2012年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2013年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2014年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2015年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2016年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2017年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2018年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2019年中债国债收益率曲线标准期限信息.xlsx',
        'data/国债及其他债券收益率曲线/2020年中债国债收益率曲线标准期限信息.xlsx',
    ];
    let avgReturns = [];
    xlsxFiles.forEach(file => {
        const workbook = XLSX.readFile(path.join(ROOT_PATH, file));
        const sheetName = workbook.SheetNames[0];
        const sheetJson = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName]);
        const tenYearReturns = sheetJson.filter(d => d['标准期限说明'] === '0d').map(d => parseFloat(d['收益率(%)'], 10));
        avgReturns.push(tenYearReturns.reduce((acc, cur) => cur + acc) / tenYearReturns.length);
    });
    return [arr, avgReturns];
}).then(([cybReturns, gzReturns]) => {
    analyse(cybReturns.map(d => d.r));
    analyse(gzReturns.map(v => v / 100));
});
