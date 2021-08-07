import ReactDOM from 'react-dom';
import React from 'react';
import App from './App.js';

// function renderTable() {
//     const tableElem = document.createElement('table');
//     const thead = `
//         <thead>
//             <tr>
//                 <th>名称</th>
//                 <th>描述</th>
//                 <th>更新频率</th>
//                 <th>本地更新时间</th>
//                 <th>操作</th>
//             </tr>
//         </thead>
//     `;
//     const tbody = indicators.map(d => `
//         <tr>
//             <td>${d.name}</td>
//             <td>${d.desc}</td>
//             <td></td>
//             <td></td>
//             <td>
//                 <a href="${d.url}">查看</a>
//                 <a href="javascript:void(0);" data-action="${d.name}">更新</a>
//             </td>
//         </tr>
//     `).join('');
//     tableElem.innerHTML = thead + tbody;
//     return tableElem;
// }

// document.body.appendChild(renderTable());

// document.body.addEventListener('click', (e) => {

//     const action = e.target.dataset.action;
//     if (action) {
//         fetch(`/api/update?name=${action}`)
//             .then(res => res.json())
//             .then(json => {
//                 if (json.code === 200) alert('更新成功！');
//             });
//     }

// });

ReactDOM.render(
    <App />,
    document.getElementById('app')
);
