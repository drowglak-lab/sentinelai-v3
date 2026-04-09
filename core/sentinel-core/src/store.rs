use crate::models::{Policy, PolicyConfig};
use lazy_static::lazy_static;
use std::collections::HashMap;
use std::fs;
use std::sync::{Arc, RwLock};

// Снапшот для безопасного многопоточного чтения без блокировок
pub struct PolicySnapshot {
    pub by_tool: HashMap<String, Vec<Policy>>,
}

// Главное хранилище политик
pub struct PolicyStore {
    policies: RwLock<HashMap<String, Vec<Policy>>>,
}

impl PolicyStore {
    pub fn new() -> Self {
        Self {
            policies: RwLock::new(HashMap::new()),
        }
    }

    pub fn load_from_file(&self, path: &str) -> Result<usize, String> {
        let content = fs::read_to_string(path).map_err(|e| format!("Failed to read YAML: {}", e))?;
        
        // Парсим наш новый сложный YAML с рекурсивными условиями
        let config: PolicyConfig = serde_yaml::from_str(&content).map_err(|e| format!("YAML Parse Error: {}", e))?;
        
        let mut map: HashMap<String, Vec<Policy>> = HashMap::new();
        let mut count = 0;
        
        for policy in config.policies {
            map.entry(policy.tool_name.clone())
                .or_insert_with(Vec::new)
                .push(policy);
            count += 1;
        }
        
        // Обновляем память
        let mut write_guard = self.policies.write().unwrap();
        *write_guard = map;
        
        Ok(count)
    }

    pub fn get_snapshot(&self) -> Arc<PolicySnapshot> {
        let read_guard = self.policies.read().unwrap();
        Arc::new(PolicySnapshot {
            by_tool: read_guard.clone(),
        })
    }
}

// Создаем ту самую глобальную переменную, которую искал компилятор
lazy_static! {
    pub static ref POLICY_STORE: PolicyStore = PolicyStore::new();
}
