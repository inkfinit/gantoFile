use serde::Serialize;
use std::path::Path;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FileMetadata {
    pub path: String,
    pub name: String,
    pub size: u64,
    pub dir: String,
}

#[tauri::command]
fn get_file_metadata(path: String) -> Result<FileMetadata, String> {
    let target = Path::new(&path);
    let meta = std::fs::metadata(target)
        .map_err(|err| format!("Failed to read file metadata: {err}"))?;

    if !meta.is_file() {
        return Err("Selected path is not a valid file.".to_string());
    }

    let name = target
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| path.clone());

    let dir = target
        .parent()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();

    Ok(FileMetadata {
        path,
        name,
        size: meta.len(),
        dir,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![get_file_metadata])
        .run(tauri::generate_context!())
        .expect("error while running GantoFile application");
}
