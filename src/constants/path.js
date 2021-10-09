import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export const ROOT_PATH = path.resolve(__dirname, '../../');
export const DATA_STORE_PATH = path.resolve(ROOT_PATH, 'data');