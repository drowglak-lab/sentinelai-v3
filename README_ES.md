# SentinelAI v3.0: El Firewall de Acciones para Agentes Autónomos 🛡️🤖

**La Capa de Seguridad de Alto Rendimiento para Operaciones Bancarias Impulsadas por IA.**

SentinelAI es un **Action Firewall** (Cortafuegos de Acciones) de grado Enterprise diseñado para cerrar la brecha entre los agentes autónomos de IA y los estrictos requisitos de seguridad financiera. En una era donde los LLM (Modelos de Lenguaje Grande) ejecutan código y manejan transacciones, SentinelAI garantiza que cada acción sea validada, anonimizada y registrada criptográficamente antes de tocar el sistema bancario central.



---

## 🏛️ Arquitectura Zero-Trust de Tres Capas

SentinelAI v3.0 ha evolucionado de un simple proxy a un gateway distribuido y tolerante a fallos que opera en tres capas distintas:

1. **L2 - Lógica de Negocio (Dynamic Policy Engine):**
   * Lee reglas declarativas desde `policies.yaml`.
   * Evalúa dinámicamente las reglas ABAC (Control de Acceso Basado en Atributos) y RBAC (Basado en Roles) mediante esquemas de Pydantic. 
   * *Cero hardcode:* Los límites de seguridad se pueden actualizar sin necesidad de recompilar ni redesplegar el servicio.
2. **L1 - Plano de Control (FastAPI + Redis):**
   * Actúa como orquestador de tráfico con inyección de dependencias (Dependency Injection) estricta y gestión controlada del ciclo de vida (Graceful Lifespan).
   * Se conecta a un clúster de Redis para monitorizar el estado del sistema. 
   * Implementa un **Protocolo de Recuperación Adaptativa (Ramp-Up)**, mitigando ataques de "Thundering Herd" (Estampida) permitiendo el tráfico gradualmente (ej. 20% de capacidad) durante la reactivación del sistema.
3. **L0 - Plano de Datos y Ejecutor (Rust + RocksDB):**
   * Un motor central escrito en Rust con latencia inferior a 15ms.
   * Utiliza una instancia incrustada de RocksDB como capa de memoria inmutable.
   * **Autodefensa Autónoma:** Si el motor de Rust detecta una discrepancia criptográfica entre los datos entrantes y el registro en RocksDB, activa un interruptor de emergencia (`FAIL_SAFE`) atómico y local, congelando el nodo al instante sin esperar intervención humana.



---

## 🧪 El Viaje de la Ingeniería y Experimentos

Construir SentinelAI no fue un camino recto. Fue un proceso iterativo de pruebas de estrés, fallos y evolución. Aquí está el análisis post-mortem de nuestros experimentos arquitectónicos:

* **Experimento 1: Superando el GIL de Python**
  * *Desafío:* El threading estándar de Python alcanzó un "techo de cristal" durante las pruebas de carga (limitado a ~280 RPS con alta latencia).
  * *Solución:* Eludimos el Global Interpreter Lock (GIL) utilizando conceptos del PEP 734 (Múltiples Intérpretes) y reescribiendo la pesada evaluación criptográfica en Rust mediante `pyo3`/`maturin`.
* **Experimento 2: El Kill-Switch Distribuido**
  * *Desafío:* Un agente comprometido podría inundar el sistema antes de que un administrador pudiera apagar manualmente el servidor FastAPI.
  * *Solución:* Construimos un kill-switch de dos niveles. Una herramienta externa `admin_panel.py` transmite estados de emergencia vía Redis (L1). Simultáneamente, el núcleo de Rust mantiene un booleano atómico en memoria (L0). Si cualquiera de los dos se activa, el sistema devuelve inmediatamente `503 SYSTEM_FROZEN`.
* **Experimento 3: Sobreviviendo a la "Auditoría de Código" (Refactorización Enterprise)**
  * *Desafío:* Las primeras versiones dependían de variables globales, políticas de seguridad hardcodeadas (`dict`) y carecían de una gestión segura del ciclo de vida: la clásica deuda técnica de los prototipos.
  * *Solución:* Llevamos a cabo una refactorización masiva a nivel Enterprise. Implementamos inyección de dependencias (`Depends()`), reemplazamos los diccionarios con esquemas estrictos `BaseModel` de Pydantic para la validación de peticiones, introdujimos `Enum` para la seguridad de los estados, y movimos todas las configuraciones a `.env` usando `pydantic-settings`.

---

## ⚖️ Cumplimiento Normativo (Preparado para la DORA de la UE)

Diseñado teniendo en cuenta la **Ley de Resiliencia Operativa Digital (DORA)**:
* **Integridad:** El encadenamiento Merkle con SHA-256 garantiza que los datos de auditoría permanezcan criptográficamente a prueba de manipulaciones.
* **Recuperabilidad:** La sincronización de estado con Redis permite al gateway reanudar de forma segura la cadena de auditoría tras fallos del sistema mediante fases de Ramp-Up controladas.
* **Rendimiento:** Los requisitos del trading de alta frecuencia se cumplen aislando las operaciones lentas de I/O del núcleo de validación en Rust.

---

## 📂 Stack Tecnológico
* **Lenguaje:** Python 3.12+ y **Rust** (Seguridad y velocidad de microsegundos).
* **Frameworks:** FastAPI (Orquestación Asíncrona), Pydantic (Validación), Maturin (Puente Rust-Python).
* **Infraestructura:** Docker & Docker Compose, **Redis** (Gestión de Estado), **RocksDB** (Almacenamiento incrustado de alta velocidad).
* **Seguridad:** Firmas RSA, Encadenamiento SHA-256, Motor de Políticas ABAC/RBAC.

---

## 🚀 Inicio Rápido (Despliegue Enterprise)

Todo el ecosistema está contenerizado para un despliegue consistente.

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-repo/sentinel-ai.git

# 2. Iniciar el Secure Gateway, Redis y el Servicio de Auditoría SIEM
docker-compose up --build
```

### 🎮 Demostración en Vivo: El Plano de Control

Puedes interactuar con el Kill-Switch distribuido y el Policy Engine en tiempo real utilizando la herramienta CLI de administración incluida:

```bash
# Activar un bloqueo global inmediato (devuelve 503 SYSTEM_FROZEN)
python admin_panel.py FROZEN

# Revivir lentamente el sistema, permitiendo solo el 20% del tráfico (devuelve 429 para peticiones bloqueadas)
python admin_panel.py RAMP_UP 0.2

# Volver a la capacidad total
python admin_panel.py NORMAL
```

---

## 👨‍💻 Desarrollador
**Aleksei Matveenko** | *AI Software Engineer*
Especializado en Seguridad de Ejecución de IA, Sistemas Distribuidos y Arquitectura Backend de Alto Rendimiento.
📍 Valencia, España (Listo para complejos desafíos Fintech en la UE).
