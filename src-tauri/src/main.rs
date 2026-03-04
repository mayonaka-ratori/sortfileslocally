// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::io::{BufRead, BufReader};
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use tauri::{Manager, State, AppHandle, Emitter};

struct AppState {
    port: Mutex<Option<u16>>,
    backend_child: Mutex<Option<Child>>,
    restart_count: Mutex<u32>,
    sidecar_path: Mutex<Option<std::path::PathBuf>>,
    is_shutting_down: Arc<AtomicBool>,
}

#[derive(serde::Serialize)]
struct BackendStatus {
    port: Option<u16>,
    is_running: bool,
    restart_count: u32,
}

#[tauri::command]
fn get_backend_port(state: State<AppState>) -> Result<u16, String> {
    let port = state.port.lock().unwrap();
    port.ok_or_else(|| "Backend port not yet discovered".to_string())
}

#[tauri::command]
fn get_backend_status(state: State<AppState>) -> Result<BackendStatus, String> {
    let port = *state.port.lock().unwrap();
    let is_running = state.backend_child.lock().unwrap().is_some();
    let restart_count = *state.restart_count.lock().unwrap();
    
    Ok(BackendStatus {
        port,
        is_running,
        restart_count,
    })
}

#[tauri::command]
fn restart_backend(state: State<AppState>, app_handle: AppHandle) -> Result<String, String> {
    let mut child_guard = state.backend_child.lock().unwrap();
    if let Some(mut child) = child_guard.take() {
        let _ = child.kill();
    }
    
    *state.restart_count.lock().unwrap() = 0;
    
    let path_guard = state.sidecar_path.lock().unwrap();
    if let Some(path) = path_guard.as_ref() {
        match spawn_and_discover_port(path.clone(), &state) {
            Ok(child) => {
                *child_guard = Some(child);
                let _ = app_handle.emit("backend-restarted", ());
                Ok("Backend restarted successfully".to_string())
            }
            Err(e) => {
                let _ = app_handle.emit("backend-crashed", e.clone());
                Err(format!("Failed to restart backend: {}", e))
            }
        }
    } else {
        Err("Sidecar path not resolved".to_string())
    }
}

fn spawn_and_discover_port(path: std::path::PathBuf, state: &AppState) -> Result<Child, String> {
    let mut cmd = Command::new(path);
    cmd.stdout(Stdio::piped()).stderr(Stdio::inherit());
    
    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    
    let stdout = child.stdout.take().ok_or("Failed to open stdout")?;
    let reader = BufReader::new(stdout);
    
    let start_time = Instant::now();
    let mut discovered_port = None;
    
    for line in reader.lines() {
        if let Ok(l) = line {
            println!("Sidecar: {}", l);
            if l.contains("STARTING_PORT=") {
                if let Some(port_str) = l.split('=').last() {
                    if let Ok(port) = port_str.trim().parse::<u16>() {
                        discovered_port = Some(port);
                        break;
                    }
                }
            }
        }
        if start_time.elapsed() > Duration::from_secs(30) {
            break;
        }
    }
    
    if let Some(port) = discovered_port {
        *state.port.lock().unwrap() = Some(port);
        println!("Discovered backend port: {}", port);
        Ok(child)
    } else {
        let _ = child.kill();
        Err("Failed to discover backend port within 30s".to_string())
    }
}

fn start_health_monitor(app_handle: AppHandle) {
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(Duration::from_secs(3));
            
            let state = app_handle.state::<AppState>();
            if state.is_shutting_down.load(Ordering::SeqCst) {
                break;
            }
            
            let mut is_exited = false;
            let mut exit_code = None;
            
            {
                let mut child_guard = state.backend_child.lock().unwrap();
                if let Some(child) = child_guard.as_mut() {
                    if let Ok(Some(status)) = child.try_wait() {
                        is_exited = true;
                        exit_code = status.code();
                    }
                }
            }
            
            if is_exited {
                println!("Sidecar process exited unexpectedly. Exit code: {:?}", exit_code);
                
                let current_restarts = {
                    let mut rc = state.restart_count.lock().unwrap();
                    *rc += 1;
                    *rc
                };
                
                if current_restarts <= 3 {
                    println!("Attempting to restart sidecar (attempt {}/3)...", current_restarts);
                    std::thread::sleep(Duration::from_secs(2));
                    
                    let path_guard = state.sidecar_path.lock().unwrap();
                    if let Some(path) = path_guard.as_ref() {
                        match spawn_and_discover_port(path.clone(), &state) {
                            Ok(new_child) => {
                                let mut child_guard = state.backend_child.lock().unwrap();
                                *child_guard = Some(new_child);
                                println!("Restart successful.");
                                let _ = app_handle.emit("backend-restarted", ());
                            }
                            Err(e) => {
                                eprintln!("Restart failed: {}", e);
                            }
                        }
                    }
                } else {
                    eprintln!("Failed to restart sidecar after 3 attempts.");
                    let _ = app_handle.emit("backend-crashed", "Exceeded max restart attempts");
                    break;
                }
            }
        }
    });
}

fn main() {
    let is_shutting_down = Arc::new(AtomicBool::new(false));
    let shutdown_flag_for_app = is_shutting_down.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(AppState {
            port: Mutex::new(None),
            backend_child: Mutex::new(None),
            restart_count: Mutex::new(0),
            sidecar_path: Mutex::new(None),
            is_shutting_down: is_shutting_down,
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_port,
            get_backend_status,
            restart_backend
        ])
        .setup(|app| {
            #[cfg(target_os = "windows")]
            let sidecar_name = "localcurator-backend.exe";
            #[cfg(not(target_os = "windows"))]
            let sidecar_name = "localcurator-backend";

            let resource_path = app.path().resolve(
                format!("binaries/{}", sidecar_name),
                tauri::path::BaseDirectory::Resource
            );
            
            let handle = app.handle().clone();
            
            match resource_path {
                Ok(path) => {
                    if path.exists() {
                        let state = handle.state::<AppState>();
                        *state.sidecar_path.lock().unwrap() = Some(path.clone());
                        
                        match spawn_and_discover_port(path, &state) {
                            Ok(child) => {
                                *state.backend_child.lock().unwrap() = Some(child);
                                
                                #[cfg(not(debug_assertions))]
                                start_health_monitor(handle);
                            }
                            Err(e) => {
                                eprintln!("Failed to spawn sidecar initially: {}", e);
                            }
                        }
                    } else {
                        eprintln!("Sidecar binary not found at {:?}", path);
                    }
                }
                Err(e) => {
                    eprintln!("Failed to resolve sidecar path: {}", e);
                }
            }

            Ok(())
        })
        .on_window_event(move |window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                shutdown_flag_for_app.store(true, Ordering::SeqCst);
                
                let state = window.state::<AppState>();
                let mut guard = state.backend_child.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    let _ = child.kill();
                    println!("Killed backend sidecar process");
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
