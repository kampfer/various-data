export default [
    {
        name: 'cpi',
        desc: '全国居民消费价格指数（上月=100）',
        crawler: './crawlers/cpi.js',
    },
    {
        name: 'moneySupply',
        desc: '中国 货币供应量',
        crawler: './crawlers/moneySupply.js',
    },
    {
        name: 'ticketPutAndBackStatByMonth',
        desc: '货币净投放与净回笼',
        crawler: './crawlers/ticketPutAndBackStatByMonth.js',
    },
    {
        name: 'fr_fdr',
        desc: '回购定盘利率和银银间回购定盘利率',
        crawler: './crawlers/fr_fdr.js',
    },
    {
        name: 'rmbCFETSIndex',
        desc: 'CFETS人民币汇率指数',
        crawler: './crawlers/rmbCFETSIndex.js',
    },
    {
        name: 'balanceSheetOfMonetaryAuthority',
        desc: '货币当局资产负债表',
        crawler: './crawlers/balanceSheetOfMonetaryAuthority.js'
    }
];
