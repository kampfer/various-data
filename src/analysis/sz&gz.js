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

Promise.all([
    request.get({
        url: 'http://127.0.0.1:3000/api/getIndicator',
        data: {
            id: '3b065983-7795-40dc-b104-48c072803d33'
        }
    })
    .then(res => res.json()),
    request.get({
        url: 'http://127.0.0.1:3000/api/getIndicator',
        data: {
            id: '875ee100-a14e-41aa-8c22-ea3fdc106792'
        }
    })
    .then(res => res.json())
]).then(([{ data: data }, { data: data2 }]) => {

    // 创业板
    let prevValue;
    let prevDate;
    const cybReturns = [];
    for(let i = 0, l = data.length; i < l; i++) {
        let item = data[i];
        let time = moment(data[i].date);
        if (i === 0) {
            prevValue = parseFloat(item.close, 10);
            prevDate = moment(item.date).format('YYYY-MM-DD');
        } else {
            let nextItem = data[i + 1];
            let endDate;
            if (!nextItem) {
                endDate = moment(item.date).format('YYYY-MM-DD');
            } else if(moment(nextItem.date).year() !== time.year()) {
                endDate = moment(item.date).format('YYYY-MM-DD');
            }
            if (endDate) {
                const end = parseFloat(item.close, 10);
                cybReturns.push({
                    start: prevValue,
                    end: end,
                    r: (end - prevValue) / prevValue,
                    startDate: prevDate,
                    endDate: endDate
                });
                prevValue = end;
                prevDate = endDate;
            }
        }
    }

    // cpi
    const cpis = data2.map(d => ({
        value: (d.cpi - 100) / 100,
        date: moment(d.date).format('YYYY')
    }));

    // 短期国债
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
    let gzReturns = [];
    let startDate = 2011;
    xlsxFiles.forEach(file => {
        const workbook = XLSX.readFile(path.join(ROOT_PATH, file));
        const sheetName = workbook.SheetNames[0];
        const sheetJson = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName]);
        const tenYearReturns = sheetJson.filter(d => d['标准期限说明'] === '0d').map(d => parseFloat(d['收益率(%)'], 10));
        gzReturns.push({
            value: tenYearReturns.reduce((acc, cur) => cur + acc) / tenYearReturns.length/ 100,
            date: startDate++
        });
    });

    return [cybReturns.slice(1, -1), gzReturns, cpis.slice(0, -1).reverse()];

}).then(([cybReturns, gzReturns, cpis]) => {
    console.log(cybReturns, gzReturns, cpis);
    analyse(cybReturns.map(d => d.r));
    analyse(gzReturns.map(d => d.value));
    const sjsy = [];
    for(let i = 0; i < 10; i++) {
        sjsy.push(cybReturns[i].r - gzReturns[i].value - cpis[i].value);
    }
    analyse(sjsy);
});
