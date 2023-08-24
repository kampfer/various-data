import ReactDOM from 'react-dom/client';
import React from 'react';
import { Provider } from 'react-redux';
import store from './store/index.js';
import router from './router.js';
import {
    RouterProvider,
} from 'react-router-dom';

import 'normalize.css';
import './main.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <Provider store={store}>
        <RouterProvider router={router} />
    </Provider>
);
