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
    }
];

function renderTable() {
    const tableElem = document.createElement('table');
    const thead = `
        <thead>
            <tr>
                <th>名称</th>
                <th>描述</th>
                <th>操作</th>
            </tr>
        </thead>
    `;
    const tbody = routers.map(d => `
        <tr>
            <td>${d.name}</td>
            <td>${d.desc}</td>
            <td><a href="${d.url}">查看</a></td>
        </tr>
    `).join('');
    tableElem.innerHTML = thead + tbody;
    return tableElem;
}

document.body.appendChild(renderTable());
