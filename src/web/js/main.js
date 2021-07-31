const routers = [
    {
        name: 'cpi',
        desc: 'cpi',
        url: './cpi.html',
    },
    {
        name: 'moneySupply',
        desc: 'moneySupply',
        url: './moneySupply.html',
    },
    {
        name: 'ticketPutAndBackStatByMonth',
        desc: 'ticketPutAndBackStatByMonth',
        url: './ticketPutAndBackStatByMonth.html',
    },
    {
        name: 'fr_fdr',
        desc: 'fr_fdr',
        url: './frfdr.html',
    },
    {
        name: 'rmbCFETSIndex',
        desc: 'CFETS人民币汇率指数',
        url: './rmbCFETSIndex.html',
    }
];

function renderTable() {
    const tableElem = document.createElement('table');
    const thead = `
        <thead>
            <tr>
                <th>名称</th>
                <th>描述</th>
                <th>更新频率</th>
                <th>本地更新时间</th>
                <th>操作</th>
            </tr>
        </thead>
    `;
    const tbody = routers.map(d => `
        <tr>
            <td>${d.name}</td>
            <td>${d.desc}</td>
            <td></td>
            <td></td>
            <td>
                <a href="${d.url}">查看</a>
                <a href="javascript:void(0);" data-action="${d.name}">更新</a>
            </td>
        </tr>
    `).join('');
    tableElem.innerHTML = thead + tbody;
    return tableElem;
}

document.body.appendChild(renderTable());

document.body.addEventListener('click', (e) => {

    const action = e.target.dataset.action;
    if (action) {
        fetch(`/api/update?name=${action}`).then(res => alert('更新成功！'));
    }

});
