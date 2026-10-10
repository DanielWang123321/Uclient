mod sidecar;

use sidecar::{Engine, Handshake};
use std::time::Duration;
use tauri::{Manager, RunEvent};

#[tauri::command]
async fn engine_handshake(engine: tauri::State<'_, Engine>) -> Result<Handshake, String> {
    let e = engine.inner().clone();
    tauri::async_runtime::spawn_blocking(move || e.wait_handshake(Duration::from_secs(60)))
        .await
        .map_err(|e| e.to_string())?
}

/// Writes a text file chosen by the user through the native save dialog (CSV/JSON export).
#[tauri::command]
fn write_text_file(path: String, contents: String) -> Result<(), String> {
    std::fs::write(&path, contents).map_err(|e| format!("cannot write {path}: {e}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let engine = Engine::default();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(engine.clone())
        .setup(|app| {
            app.state::<Engine>().start(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_handshake, write_text_file])
        .build(tauri::generate_context!())
        .expect("error while building Uclient");
    app.run(move |_, ev| {
        if let RunEvent::Exit = ev {
            engine.shutdown();
        }
    });
}
