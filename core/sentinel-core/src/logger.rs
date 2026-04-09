use std::fs::OpenOptions;
use std::io::Write;
use std::sync::mpsc::{self, Sender};
use std::thread;
use serde::Serialize;

#[derive(Serialize)]
pub struct AuditEntry {
    pub timestamp: String,
    pub tool: String,
    pub risk: f32,
    pub decision: String,
    pub shadow_decision: String,
    pub is_diff: bool,
    pub policy_id: String,
    pub latency_ns: u64,
}

pub fn start_logger() -> Sender<AuditEntry> {
    let (tx, rx) = mpsc::channel::<AuditEntry>();
    thread::spawn(move || {
        let file_result = OpenOptions::new().create(true).append(true).open("sentinel_audit.log");
        if let Ok(mut file) = file_result {
            while let Ok(entry) = rx.recv() {
                if let Ok(json) = serde_json::to_string(&entry) {
                    let _ = writeln!(file, "{}", json);
                }
            }
        }
    });
    tx
}
