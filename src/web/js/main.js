import routers from './routers.js';

function renderTable() {
    let tableElem = document.querySelector('#list');
    if (!tableElem) {
        tableElem = document.createElement('table');
        tableElem.id = 'list';
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
                <td><a href="#${d.name}">查看</a></td>
            </tr>
        `).join('');
        tableElem.innerHTML = thead + tbody;
        document.body.appendChild(tableElem);
    } else {
        tableElem.style.display = 'unset';
    }
}

function handleHashChange() {
    const hash = location.hash.substr(1);
    const router = routers.find(d => d.name === hash);
    if (router) {
        const tableElem = document.querySelector('#list');
        if (tableElem) tableElem.style.display = 'none';
        import(router.script).then(() => console.log(`加载`, router));
    } else {
        renderTable();
    }
}

window.addEventListener('hashchange', handleHashChange);

handleHashChange();
