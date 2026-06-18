use kmbox_net::{KmboxNet, MonitorPacket};
use std::net::UdpSocket;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

fn load_env() -> std::collections::HashMap<String, String> {
    let mut map = std::collections::HashMap::new();
    if let Ok(content) = std::fs::read_to_string(".env") {
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') { continue; }
            if let Some((key, val)) = line.split_once('=') {
                map.insert(key.trim().to_string(), val.trim().to_string());
            }
        }
    }
    map
}

fn get_var(env: &std::collections::HashMap<String, String>, key: &str) -> String {
    env.get(key)
        .cloned()
        .or_else(|| std::env::var(key).ok())
        .unwrap_or_else(|| panic!("set {key} in .env or environment"))
}

fn main() {
    let env = load_env();
    let ip = get_var(&env, "KMBOX_IP");
    let port: u16 = get_var(&env, "KMBOX_PORT").parse().unwrap();
    let uuid = get_var(&env, "KMBOX_UUID");

    println!("=== KmboxNet E2E Test ===");
    println!("connecting to {ip}:{port} ...\n");

    let mut km = KmboxNet::new(&ip, port, &uuid).expect("connection failed");
    println!("[OK] connected\n");

    // --- test 1: mouse move (square pattern) ---
    println!("--- 1. mouse move (square) ---");
    println!("watch your cursor...");
    thread::sleep(Duration::from_secs(1));
    for _ in 0..2 {
        km.move_rel(150, 0).expect("move failed");
        println!("  -> right 150px");
        thread::sleep(Duration::from_secs(1));
        km.move_rel(0, 150).expect("move failed");
        println!("  -> down 150px");
        thread::sleep(Duration::from_secs(1));
        km.move_rel(-150, 0).expect("move failed");
        println!("  -> left 150px");
        thread::sleep(Duration::from_secs(1));
        km.move_rel(0, -150).expect("move failed");
        println!("  -> up 150px");
        thread::sleep(Duration::from_secs(1));
    }

    // --- test 2: mask_x (X axis blocked for 3 sec) ---
    println!("\n--- 2. mask_x ---");
    println!("  X axis BLOCKED for 3 sec — try moving mouse left/right");
    km.mask_x(true).expect("mask_x failed");
    thread::sleep(Duration::from_secs(3));
    km.mask_x(false).expect("unmask_x failed");
    println!("  X axis restored");

    // --- test 3: mask_y (Y axis blocked for 3 sec) ---
    println!("\n--- 3. mask_y ---");
    println!("  Y axis BLOCKED for 3 sec — try moving mouse up/down");
    km.mask_y(true).expect("mask_y failed");
    thread::sleep(Duration::from_secs(3));
    km.mask_y(false).expect("unmask_y failed");
    println!("  Y axis restored");

    // --- test 4: mask_left (left click blocked for 3 sec) ---
    println!("\n--- 4. mask_left ---");
    println!("  left click BLOCKED for 3 sec — try clicking");
    km.mask_left(true).expect("mask_left failed");
    thread::sleep(Duration::from_secs(3));
    km.unmask_all().expect("unmask_all failed");
    println!("  all masks cleared");

    // --- test 5: monitor ---
    println!("\n--- 5. monitor ---");
    let monitor_port = 5002u16;
    let ok = km.start_monitor(monitor_port).expect("start_monitor failed");
    println!("[{}] start_monitor on port {monitor_port}", if ok { "OK" } else { "FAIL" });

    if ok {
        let mon_sock = UdpSocket::bind(format!("0.0.0.0:{monitor_port}")).expect("bind failed");
        mon_sock.set_read_timeout(Some(Duration::from_millis(10))).unwrap();

        let mouse_state = Arc::new(Mutex::new((0u8, 0i16, 0i16)));
        let state = mouse_state.clone();
        let running = Arc::new(std::sync::atomic::AtomicBool::new(true));
        let r = running.clone();

        let listener = thread::spawn(move || {
            let mut buf = [0u8; 1024];
            while r.load(std::sync::atomic::Ordering::Relaxed) {
                if let Ok((n, _)) = mon_sock.recv_from(&mut buf) {
                    if let Some(pkt) = MonitorPacket::parse(&buf[..n]) {
                        let mut s = state.lock().unwrap();
                        *s = (pkt.mouse.buttons, pkt.mouse.x, pkt.mouse.y);
                    }
                }
            }
        });

        println!("  move your mouse and click for 3 sec...");
        for _ in 0..30 {
            thread::sleep(Duration::from_millis(100));
            let (buttons, x, y) = *mouse_state.lock().unwrap();
            let left = buttons & 0x01 != 0;
            let right = buttons & 0x02 != 0;
            if x != 0 || y != 0 || left || right {
                println!("  x={x:4} y={y:4} left={left} right={right}");
            }
        }

        running.store(false, std::sync::atomic::Ordering::Relaxed);
        let _ = listener.join();
    }

    // --- test 6: LCD color ---
    println!("\n--- 6. LCD color ---");
    let red: u16 = 0xF800;
    let green: u16 = 0x07E0;
    let blue: u16 = 0x001F;

    println!("  RED");
    km.lcd_color(red).expect("lcd_color failed");
    thread::sleep(Duration::from_secs(1));

    println!("  GREEN");
    km.lcd_color(green).expect("lcd_color failed");
    thread::sleep(Duration::from_secs(1));

    println!("  BLUE");
    km.lcd_color(blue).expect("lcd_color failed");
    thread::sleep(Duration::from_secs(1));

    println!("\n=== done ===");
}
