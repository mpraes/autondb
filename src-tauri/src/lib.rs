use serde::{Deserialize, Serialize};
use std::process::Command;
use tauri::{Emitter, Manager};

#[derive(Debug, Serialize, Deserialize, Clone)]
struct MigrationConfig {
    source_dialect: String,
    source_dsn: String,
    target_dialect: String,
    target_dsn: String,
    ai_provider: Option<String>,
    ai_model: Option<String>,
    ai_key: String,
    batch_size: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct SchemaMappingResult {
    tables: Vec<serde_json::Value>,
    warnings: Vec<String>,
    target_dialect: String,
    ddl: String,
}

#[tauri::command]
async fn analyze_schema(config: MigrationConfig) -> Result<SchemaMappingResult, String> {
    let config_json = serde_json::to_string(&config).map_err(|e| e.to_string())?;
    let python_bin = get_python_bin()?;

    let output = Command::new(&python_bin)
        .args(["-m", "src.bridge", "analyze", &config_json])
        .output()
        .map_err(|e| format!("Failed to execute Python bridge: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python analyze failed: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let line = stdout.lines().next().ok_or("No output from Python bridge")?;
    let event: serde_json::Value =
        serde_json::from_str(line).map_err(|e| format!("Invalid JSON from bridge: {}", e))?;

    let payload = event
        .get("payload")
        .ok_or("Missing payload in bridge response")?;

    let result: SchemaMappingResult =
        serde_json::from_value(payload.clone()).map_err(|e| format!("Invalid mapping: {}", e))?;

    Ok(result)
}

#[tauri::command]
async fn start_migration(
    app: tauri::AppHandle,
    config: MigrationConfig,
    mapping: serde_json::Value,
) -> Result<(), String> {
    let config_json = serde_json::to_string(&config).map_err(|e| e.to_string())?;
    let mapping_json = serde_json::to_string(&mapping).map_err(|e| e.to_string())?;
    let python_bin = get_python_bin()?;

    let app_handle = app.clone();
    std::thread::spawn(move || {
        let output = Command::new(&python_bin)
            .args([
                "-m",
                "src.bridge",
                "migrate",
                &config_json,
                &mapping_json,
            ])
            .output();

        match output {
            Ok(out) => {
                let stdout = String::from_utf8_lossy(&out.stdout);
                for line in stdout.lines() {
                    if let Ok(event) = serde_json::from_str::<serde_json::Value>(line) {
                        let event_type = event["event"].as_str().unwrap_or("unknown");
                        let payload = event.get("payload").cloned().unwrap_or(serde_json::Value::Null);

                        let tauri_event = match event_type {
                            "migration_progress" => "migration-progress",
                            "migration_complete" => "migration-complete",
                            "migration_error" => "migration-error",
                            _ => continue,
                        };

                        let _ = app_handle.emit(tauri_event, payload);
                    }
                }
                if !out.status.success() {
                    let stderr = String::from_utf8_lossy(&out.stderr);
                    let _ = app_handle.emit("migration-error", stderr);
                }
            }
            Err(e) => {
                let _ = app_handle.emit(
                    "migration-error",
                    format!("Failed to execute Python bridge: {}", e),
                );
            }
        }
    });

    Ok(())
}

#[tauri::command]
async fn download_audit_pdf() -> Result<String, String> {
    let audit_dir = dirs::document_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("AutonDB");

    std::fs::create_dir_all(&audit_dir).map_err(|e| e.to_string())?;

    let path = audit_dir.join("audit_report.txt");
    std::fs::write(&path, "Audit report placeholder — full PDF generation requires a PDF library.\n")
        .map_err(|e| e.to_string())?;

    Ok(path.to_string_lossy().to_string())
}

fn get_python_bin() -> Result<String, String> {
    if cfg!(target_os = "windows") {
        Ok("autondb-core.exe".to_string())
    } else {
        Ok("autondb-core".to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            analyze_schema,
            start_migration,
            download_audit_pdf,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
