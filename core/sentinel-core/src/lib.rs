use pyo3::prelude::*;
use std::sync::atomic::{AtomicBool, Ordering};
use rocksdb::{DB, Options};
use std::sync::Arc;

// L0 Kill-Switch: Глобальный флаг в памяти текущего процесса
static FAIL_SAFE: AtomicBool = AtomicBool::new(false);

#[pyclass]
pub struct SentinelCore {
    db: Arc<DB>,
    #[allow(dead_code)]
    redis_client: redis::Client,
}

#[pymethods]
impl SentinelCore {
    #[new]
    fn new(db_path: &str, redis_url: &str) -> PyResult<Self> {
        let mut opts = Options::default();
        opts.create_if_missing(true);
        
        let db = DB::open(&opts, db_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
        let redis_client = redis::Client::open(redis_url)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(SentinelCore { 
            db: Arc::new(db), 
            redis_client 
        })
    }

    // Проверка: заморожен ли конкретный инстанс шлюза (L0)
    fn is_frozen(&self) -> bool {
        FAIL_SAFE.load(Ordering::Relaxed)
    }

    // Активация локального Kill-Switch
    fn trigger_local_freeze(&self) {
        FAIL_SAFE.store(true, Ordering::SeqCst);
    }

    /// ГЛАВНАЯ ЛОГИКА: Проверка целостности через RocksDB
    fn audit_and_verify(&self, tx_id: &str, current_hash: &str) -> PyResult<bool> {
        // Если система уже в режиме FAIL_SAFE, сразу отсекаем
        if self.is_frozen() {
            return Ok(false);
        }

        let key = tx_id.as_bytes();
        let current_hash_bytes = current_hash.as_bytes();

        // 1. Ищем старый хэш в "памяти" (RocksDB)
        match self.db.get(key).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))? {
            Some(stored_hash) => {
                // 2. Если хэш в базе не совпадает с присланным — это попытка подмены данных!
                if stored_hash != current_hash_bytes {
                    println!("🚨 [RUST ENFORCER] INTEGRITY BREACH! tx_id: {} | mismatch detected!", tx_id);
                    self.trigger_local_freeze(); // Активируем L0 Kill-Switch
                    return Ok(false);
                }
                Ok(true)
            },
            None => {
                // 3. Если записи нет — это новая транзакция, сохраняем её хэш
                self.db.put(key, current_hash_bytes)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                Ok(true)
            }
        }
    }
}

#[pymodule]
fn sentinel_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SentinelCore>()?;
    Ok(())
}
