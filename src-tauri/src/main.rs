// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::io::{BufRead, BufReader};
use std::sync::Mutex;
use tauri::{Manager, State};
use std::time::{Duration, Instant};

struct AppState {
    port: Mutex<Option<u16>>,
    backend_child: Mutex<Option<Child>>,
}

#[tauri::command]
fn get_backend_port(state: State<AppState>) -> Result<u16, String> {
    let port = state.port.lock().unwrap();
    port.ok_or_else(|| "Backend port not yet discovered".to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(AppState {
            port: Mutex::new(None),
            backend_child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .setup(|app| {
            
            #[cfg(target_os = "windows")]
            let sidecar_name = "localcurator-backend.exe";
            #[cfg(not(target_os = "windows"))]
            let sidecar_name = "localcurator-backend";

            let resource_path = app.path().resolve(
                format!("binaries/{}", sidecar_name),
                tauri::path::BaseDirectory::Resource
            );
            
            match resource_path {
                Ok(path) => {
                    // Let's use the app handle to get the state inside the thread.
                    let handle = app.handle().clone();
                    
                    std::thread::spawn(move || {
                        let state = handle.state::<AppState>();
                        let mut cmd = Command::new(path);
                        cmd.stdout(Stdio::piped())
                           .stderr(Stdio::inherit());
                        
                        match cmd.spawn() {
                            Ok(mut child) => {
                                let stdout = child.stdout.take().expect("Failed to open stdout");
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
                                } else {
                                    eprintln!("Failed to discover backend port within 30s");
                                }
                                
                                *state.backend_child.lock().unwrap() = Some(child);
                            }
                            Err(e) => {
                                eprintln!("Failed to spawn sidecar: {}", e);
                            }
                        }
                    });
                }
                Err(e) => {
                    eprintln!("Failed to resolve sidecar path: {}", e);
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
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
