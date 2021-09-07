import React, { useEffect } from 'react';

const itemMap = {
    ForeignExchange: '外汇',
    ClaimsonOtherDepositoryCorporations: '对其他存款性公司债权',    // 央行投放
    DepositsofGovernment: '政府存款',
    CurrencyIssue: '货币发行',  // m0 + 商业银行库存现金
    DepositsofOtherDepositoryCorporations: '其他存款性公司存款'     // 法定存款准备金+超额存款准备金
};

export default function BalanceSheetOfMonetaryAuthorityGraph() {

    useEffect(() => {
        let chart;
        fetch('data/balanceSheetOfMonetaryAuthority.json')
            .then(response => response.json())
            .then(({ data }) => {
                chart = Highcharts.chart('BalanceSheetOfMonetaryAuthorityGraph', {
                    chart: {
                        type: 'line',
                        width: window.innerWidth,
                        height: window.innerHeight,
                    },
                    plotOptions: {
                        area: {
                            stacking: 'normal',
                        }
                    },
                    title: {
                        text: '央行资产负债表'
                    },
                    xAxis: {
                        type: 'datetime',
                        tickPixelInterval: window.innerWidth / 10,
                        dateTimeLabelFormats: {
                            month: '%Y-%m'
                        }
                    },
                    tooltip: {
                        dateTimeLabelFormats: {
                            day: '%Y-%m-%d',
                            month: '%Y-%m'
                        }
                    },
                    series: Object.keys(data[0]).filter(key => key in itemMap).map((key) => ({
                        name: itemMap[key],
                        data: data.map(d => {
                            if (!d[key]) console.log(`${d.date}不存在${key}`);
                            return {
                                x: d.date,
                                y: d[key]
                            };
                        })
                    }))
                });
            });

        return () => chart && chart.destroy();
    });

    return (<div id='BalanceSheetOfMonetaryAuthorityGraph'></div>);

}