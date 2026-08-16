import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import type { LedgerModule } from '../../domain/ledger/constants';
import ModuleSwitch from '../../components/InvestmentLedger/ModuleSwitch';
import styles from './index.module.scss';

/**
 * 投资交易账本父路由布局：只负责标题、模块导航和子路由出口。
 * 查询、表单和异步请求均由 HoldingsPage/HistoryPage 各自负责，避免布局层保存模块状态。
 */
export const LedgerLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  /** 菜单高亮仅由当前 URL 派生，不读取或保存 Redux 模块状态。 */
  const selectedModule: LedgerModule = location.pathname.endsWith('/history')
    ? 'history'
    : 'holdings';

  /** 直接模块切换只写入 URL 和导航意图，目标模块快照由子页面继续复用。 */
  const handleSwitch = (module: LedgerModule): void => {
    if (module === selectedModule) return;
    navigate(`/investmentLedger/${module}`, {
      state: { ledgerNavigation: 'module-switch' },
    });
  };

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>投资交易账本</h1>
      </header>
      <div className={styles.layout}>
        <ModuleSwitch selectedModule={selectedModule} onSwitch={handleSwitch} />
        <section className={styles.content} aria-label="账本内容">
          <Outlet />
        </section>
      </div>
    </main>
  );
};

export default LedgerLayout;
