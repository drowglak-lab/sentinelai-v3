use pyo3::prelude::*;
use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum PolicyValue {
    Float(f32),
    Str(String),
    Bool(bool),
    List(Vec<PolicyValue>),
}

impl<'source> FromPyObject<'source> for PolicyValue {
    fn extract_bound(ob: &Bound<'source, PyAny>) -> PyResult<Self> {
        if let Ok(val) = ob.extract::<f32>() { Ok(PolicyValue::Float(val)) }
        else if let Ok(val) = ob.extract::<String>() { Ok(PolicyValue::Str(val)) }
        else if let Ok(val) = ob.extract::<bool>() { Ok(PolicyValue::Bool(val)) }
        else if let Ok(val) = ob.extract::<Vec<PolicyValue>>() { Ok(PolicyValue::List(val)) }
        else { Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unsupported type")) }
    }
}

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ExecutionMode { Enforce, Shadow }

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum Decision { Allow, Deny, Abstain }

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AtomCondition {
    pub attr_key: String,
    pub operator: String,
    pub value: PolicyValue,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Condition {
    pub and: Option<Vec<Condition>>,
    pub or: Option<Vec<Condition>>,
    pub not: Option<Box<Condition>>,
    pub atom: Option<AtomCondition>,
}

#[pyclass]
#[derive(Clone, Serialize, Debug)]
pub struct EvaluationTrace {
    #[pyo3(get)] pub policy_id: String,
    #[pyo3(get)] pub matched: bool,
    #[pyo3(get)] pub mode: ExecutionMode,
}

#[pyclass]
pub struct EvaluationResult {
    #[pyo3(get)] pub decision: Decision,
    #[pyo3(get)] pub policy_id: String,
    #[pyo3(get)] pub shadow_decision: Decision,
    #[pyo3(get)] pub shadow_policy_id: String,
    #[pyo3(get)] pub reason: String,
    #[pyo3(get)] pub version: String,
    #[pyo3(get)] pub traces: Vec<EvaluationTrace>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Policy {
    pub id: String,
    #[serde(rename = "tool")]
    pub tool_name: String,
    pub mode: ExecutionMode,
    pub condition: Condition,
}

#[derive(Debug, Deserialize)]
pub struct PolicyConfig {
    pub version: String,
    pub policies: Vec<Policy>,
}
