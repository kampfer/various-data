import ReactDOM from 'react-dom';
import React from 'react';
import App from './App.js';

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
