import React from 'react';
import { Skeleton } from 'antd';
import { Navigate } from 'react-router-dom';
import { fetchInitialModule } from '../../api/ledger';
import type { LedgerModule } from '../../domain/ledger/constants';
import styles from './index.module.scss';

/**
 * /investmentLedger 的 index 子路由：只根据后端初始模块判定结果跳转。
 * 不写 Redux 模块字段，且使用 replace 避免默认入口留在浏览器历史栈中。
 */
const IndexRedirect: React.FC = () => {
  const [target, setTarget] = React.useState<LedgerModule | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    void fetchInitialModule()
      .then(({ module }) => {
        if (mounted) setTarget(module);
      })
      .catch((reason: unknown) => {
        if (mounted) setError(reason instanceof Error ? reason.message : '账本初始化失败');
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (target !== null) {
    return <Navigate to={`/investmentLedger/${target}`} replace />;
  }

  return (
    <section className={styles.loading} aria-label="账本加载中">
      <Skeleton active={error === null} />
      {error !== null && <p className={styles.error}>{error}</p>}
    </section>
  );
};

export default IndexRedirect;
