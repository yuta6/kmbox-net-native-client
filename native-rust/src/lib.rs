mod packet;

use std::net::{SocketAddr, UdpSocket};
use std::time::Duration;

pub use packet::{HardKeyboard, HardMouse, MonitorPacket};

const CMD_CONNECT: u32 = 0xAF3C2828;
const CMD_MOUSE_MOVE: u32 = 0xAEDE7345;
const CMD_MOUSE_LEFT: u32 = 0x9823AE8D;
const CMD_MOUSE_MIDDLE: u32 = 0x97A3AE8D;
const CMD_MOUSE_RIGHT: u32 = 0x238D8212;
const CMD_MOUSE_WHEEL: u32 = 0xFFEEAD38;
const CMD_MOUSE_AUTOMOVE: u32 = 0xAEDE7346;
const CMD_KEYBOARD_ALL: u32 = 0x123C2C2F;
const CMD_REBOOT: u32 = 0xAA8855AA;
const CMD_BEZIER_MOVE: u32 = 0xA238455A;
const CMD_MONITOR: u32 = 0x27388020;
const CMD_DEBUG: u32 = 0x27382021;
const CMD_MASK_MOUSE: u32 = 0x23234343;
const CMD_UNMASK_ALL: u32 = 0x23344343;
const CMD_SETCONFIG: u32 = 0x1D3D3323;
const CMD_SETVIDPID: u32 = 0xFFED3232;
const CMD_SHOWPIC: u32 = 0x12334883;
const CMD_TRACE_ENABLE: u32 = 0xBBCDDDAC;

const TIMEOUT: Duration = Duration::from_secs(2);

#[derive(Debug)]
pub enum Error {
    InvalidUuid,
    ConnectionFailed,
    Io(std::io::Error),
    InvalidResponse,
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Error::InvalidUuid => write!(f, "invalid UUID: must be 8 hex digits"),
            Error::ConnectionFailed => write!(f, "connection failed"),
            Error::Io(e) => write!(f, "io error: {e}"),
            Error::InvalidResponse => write!(f, "invalid response"),
        }
    }
}

impl std::error::Error for Error {}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Io(e)
    }
}

pub type Result<T> = std::result::Result<T, Error>;

struct SoftMouse {
    button: i32,
    x: i32,
    y: i32,
    wheel: i32,
    point: [i32; 10],
}

impl SoftMouse {
    fn new() -> Self {
        Self {
            button: 0,
            x: 0,
            y: 0,
            wheel: 0,
            point: [0; 10],
        }
    }

    fn to_payload(&self) -> [u8; 56] {
        let mut buf = [0u8; 56];
        buf[0..4].copy_from_slice(&self.button.to_le_bytes());
        buf[4..8].copy_from_slice(&self.x.to_le_bytes());
        buf[8..12].copy_from_slice(&self.y.to_le_bytes());
        buf[12..16].copy_from_slice(&self.wheel.to_le_bytes());
        for (i, &v) in self.point.iter().enumerate() {
            let off = 16 + i * 4;
            buf[off..off + 4].copy_from_slice(&v.to_le_bytes());
        }
        buf
    }

    fn reset_movement(&mut self) {
        self.x = 0;
        self.y = 0;
        self.wheel = 0;
    }
}

struct SoftKeyboard {
    ctrl: u8,
    reserved: u8,
    button: [u8; 10],
}

impl SoftKeyboard {
    fn new() -> Self {
        Self {
            ctrl: 0,
            reserved: 0,
            button: [0; 10],
        }
    }

    fn to_payload(&self) -> [u8; 12] {
        let mut buf = [0u8; 12];
        buf[0] = self.ctrl;
        buf[1] = self.reserved;
        buf[2..12].copy_from_slice(&self.button);
        buf
    }
}

pub struct KmboxNet {
    mac: u32,
    index: u32,
    sock: UdpSocket,
    server_addr: SocketAddr,
    soft_mouse: SoftMouse,
    soft_keyboard: SoftKeyboard,
    mask_flag: u32,
    recv_buf: [u8; 2048],
    send_buf: Vec<u8>,
}

impl KmboxNet {
    pub fn new(ip: &str, port: u16, uuid: &str) -> Result<Self> {
        let mac_bytes = hex_decode(uuid).map_err(|_| Error::InvalidUuid)?;
        if mac_bytes.len() != 4 {
            return Err(Error::InvalidUuid);
        }
        let mac = u32::from_be_bytes([mac_bytes[0], mac_bytes[1], mac_bytes[2], mac_bytes[3]]);

        let sock = UdpSocket::bind("0.0.0.0:0")?;
        sock.set_read_timeout(Some(TIMEOUT))?;
        let server_addr: SocketAddr = format!("{ip}:{port}").parse().map_err(|_| {
            std::io::Error::new(std::io::ErrorKind::InvalidInput, "invalid address")
        })?;

        let mut km = Self {
            mac,
            index: 0,
            sock,
            server_addr,
            soft_mouse: SoftMouse::new(),
            soft_keyboard: SoftKeyboard::new(),
            mask_flag: 0,
            recv_buf: [0u8; 2048],
            send_buf: Vec::with_capacity(128),
        };

        if !km.send_cmd(CMD_CONNECT, &[], None)?.0 {
            return Err(Error::ConnectionFailed);
        }

        Ok(km)
    }

    pub fn start_monitor(&mut self, port: u16) -> Result<bool> {
        let rand_override = (port as u32) | (0xAA55 << 16);
        let (ok, _) = self.send_cmd(CMD_MONITOR, &[], Some(rand_override))?;
        Ok(ok)
    }

    fn make_header(&mut self, cmd: u32, rand_override: Option<u32>) -> [u8; 16] {
        self.index += 1;
        let rand = rand_override.unwrap_or_else(rand_u32);
        let mut buf = [0u8; 16];
        buf[0..4].copy_from_slice(&self.mac.to_le_bytes());
        buf[4..8].copy_from_slice(&rand.to_le_bytes());
        buf[8..12].copy_from_slice(&self.index.to_le_bytes());
        buf[12..16].copy_from_slice(&cmd.to_le_bytes());
        buf
    }

    pub fn send_cmd(
        &mut self,
        cmd: u32,
        payload: &[u8],
        rand_override: Option<u32>,
    ) -> Result<(bool, usize)> {
        let header = self.make_header(cmd, rand_override);
        self.send_buf.clear();
        self.send_buf.extend_from_slice(&header);
        self.send_buf.extend_from_slice(payload);
        self.sock.send_to(&self.send_buf, self.server_addr)?;

        match self.sock.recv_from(&mut self.recv_buf) {
            Ok((n, addr)) => {
                if n < 16 || addr != self.server_addr {
                    return Ok((false, 0));
                }
                let resp_index = u32::from_le_bytes(
                    self.recv_buf[8..12].try_into().unwrap(),
                );
                let resp_cmd = u32::from_le_bytes(
                    self.recv_buf[12..16].try_into().unwrap(),
                );
                if resp_cmd != cmd || resp_index != self.index {
                    return Ok((false, 0));
                }
                Ok((true, n))
            }
            Err(e)
                if e.kind() == std::io::ErrorKind::TimedOut
                    || e.kind() == std::io::ErrorKind::WouldBlock =>
            {
                Ok((false, 0))
            }
            Err(e) => Err(e.into()),
        }
    }

    pub fn move_rel(&mut self, x: i32, y: i32) -> Result<bool> {
        self.soft_mouse.x = x;
        self.soft_mouse.y = y;
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_MOVE, &payload, None)?;
        self.soft_mouse.reset_movement();
        Ok(ok)
    }

    pub fn move_auto(&mut self, x: i32, y: i32, ms: u32) -> Result<bool> {
        self.soft_mouse.x = x;
        self.soft_mouse.y = y;
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_AUTOMOVE, &payload, Some(ms))?;
        self.soft_mouse.reset_movement();
        Ok(ok)
    }

    pub fn move_bezier(
        &mut self,
        x: i32, y: i32, ms: u32,
        x1: i32, y1: i32, x2: i32, y2: i32,
    ) -> Result<bool> {
        self.soft_mouse.x = x;
        self.soft_mouse.y = y;
        self.soft_mouse.point[0] = x1;
        self.soft_mouse.point[1] = y1;
        self.soft_mouse.point[2] = x2;
        self.soft_mouse.point[3] = y2;
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_BEZIER_MOVE, &payload, Some(ms))?;
        self.soft_mouse.reset_movement();
        Ok(ok)
    }

    pub fn left(&mut self, is_down: bool) -> Result<bool> {
        if is_down { self.soft_mouse.button |= 0x01; }
        else { self.soft_mouse.button &= !0x01; }
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_LEFT, &payload, None)?;
        Ok(ok)
    }

    pub fn right(&mut self, is_down: bool) -> Result<bool> {
        if is_down { self.soft_mouse.button |= 0x02; }
        else { self.soft_mouse.button &= !0x02; }
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_RIGHT, &payload, None)?;
        Ok(ok)
    }

    pub fn middle(&mut self, is_down: bool) -> Result<bool> {
        if is_down { self.soft_mouse.button |= 0x04; }
        else { self.soft_mouse.button &= !0x04; }
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_MIDDLE, &payload, None)?;
        Ok(ok)
    }

    pub fn wheel(&mut self, value: i32) -> Result<bool> {
        self.soft_mouse.wheel = value;
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_WHEEL, &payload, None)?;
        self.soft_mouse.wheel = 0;
        Ok(ok)
    }

    pub fn key_down(&mut self, vk_key: u8) -> Result<bool> {
        if (0xE0..=0xE7).contains(&vk_key) {
            self.soft_keyboard.ctrl |= 1 << (vk_key - 0xE0);
        } else {
            let already = self.soft_keyboard.button.contains(&vk_key);
            if !already {
                if let Some(slot) = self.soft_keyboard.button.iter_mut().find(|s| **s == 0) {
                    *slot = vk_key;
                } else {
                    self.soft_keyboard.button.copy_within(1.., 0);
                    self.soft_keyboard.button[9] = vk_key;
                }
            }
        }
        let payload = self.soft_keyboard.to_payload();
        let (ok, _) = self.send_cmd(CMD_KEYBOARD_ALL, &payload, None)?;
        Ok(ok)
    }

    pub fn key_up(&mut self, vk_key: u8) -> Result<bool> {
        if (0xE0..=0xE7).contains(&vk_key) {
            self.soft_keyboard.ctrl &= !(1 << (vk_key - 0xE0));
        } else if let Some(i) = self.soft_keyboard.button.iter().position(|&k| k == vk_key) {
            self.soft_keyboard.button.copy_within(i + 1.., i);
            self.soft_keyboard.button[9] = 0;
        }
        let payload = self.soft_keyboard.to_payload();
        let (ok, _) = self.send_cmd(CMD_KEYBOARD_ALL, &payload, None)?;
        Ok(ok)
    }

    pub fn mouse_all(&mut self, button: i32, x: i32, y: i32, wheel: i32) -> Result<bool> {
        self.soft_mouse.button = button;
        self.soft_mouse.x = x;
        self.soft_mouse.y = y;
        self.soft_mouse.wheel = wheel;
        let payload = self.soft_mouse.to_payload();
        let (ok, _) = self.send_cmd(CMD_MOUSE_WHEEL, &payload, None)?;
        self.soft_mouse.reset_movement();
        Ok(ok)
    }

    pub fn mask_left(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(0, enable) }
    pub fn mask_right(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(1, enable) }
    pub fn mask_middle(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(2, enable) }
    pub fn mask_side1(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(3, enable) }
    pub fn mask_side2(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(4, enable) }
    pub fn mask_x(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(5, enable) }
    pub fn mask_y(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(6, enable) }
    pub fn mask_wheel(&mut self, enable: bool) -> Result<bool> { self.set_mask_bit(7, enable) }

    fn set_mask_bit(&mut self, bit: u32, enable: bool) -> Result<bool> {
        if enable { self.mask_flag |= 1 << bit; }
        else { self.mask_flag &= !(1 << bit); }
        let (ok, _) = self.send_cmd(CMD_MASK_MOUSE, &[], Some(self.mask_flag))?;
        Ok(ok)
    }

    pub fn mask_keyboard(&mut self, vkey: u8) -> Result<bool> {
        let rand = (self.mask_flag & 0xFF) | ((vkey as u32) << 8);
        let (ok, _) = self.send_cmd(CMD_MASK_MOUSE, &[], Some(rand))?;
        Ok(ok)
    }

    pub fn unmask_keyboard(&mut self, vkey: u8) -> Result<bool> {
        let rand = (self.mask_flag & 0xFF) | ((vkey as u32) << 8);
        let (ok, _) = self.send_cmd(CMD_UNMASK_ALL, &[], Some(rand))?;
        Ok(ok)
    }

    pub fn unmask_all(&mut self) -> Result<bool> {
        self.mask_flag = 0;
        let (ok, _) = self.send_cmd(CMD_UNMASK_ALL, &[], Some(0))?;
        Ok(ok)
    }

    pub fn set_config(&mut self, ip: &str, port: u16) -> Result<bool> {
        let ip_addr: std::net::Ipv4Addr = ip.parse().map_err(|_| {
            std::io::Error::new(std::io::ErrorKind::InvalidInput, "invalid IP")
        })?;
        let ip_int = u32::from(ip_addr);
        let payload = port.to_be_bytes();
        let (ok, _) = self.send_cmd(CMD_SETCONFIG, &payload, Some(ip_int))?;
        Ok(ok)
    }

    pub fn reboot(&mut self) -> Result<bool> {
        let (ok, _) = self.send_cmd(CMD_REBOOT, &[], None)?;
        Ok(ok)
    }

    pub fn debug(&mut self, port: u16, enable: bool) -> Result<bool> {
        let rand = (port as u32) | ((enable as u32) << 16);
        let (ok, _) = self.send_cmd(CMD_DEBUG, &[], Some(rand))?;
        Ok(ok)
    }

    pub fn set_vid_pid(&mut self, vid: u16, pid: u16) -> Result<bool> {
        let mut payload = [0u8; 4];
        payload[0..2].copy_from_slice(&vid.to_le_bytes());
        payload[2..4].copy_from_slice(&pid.to_le_bytes());
        let (ok, _) = self.send_cmd(CMD_SETVIDPID, &payload, None)?;
        Ok(ok)
    }

    pub fn trace_enable(&mut self, enable: bool) -> Result<bool> {
        let rand = u32::from(enable);
        let (ok, _) = self.send_cmd(CMD_TRACE_ENABLE, &[], Some(rand))?;
        Ok(ok)
    }

    pub fn lcd_color(&mut self, rgb565: u16) -> Result<bool> {
        let row: Vec<u8> = (0..512).flat_map(|_| rgb565.to_le_bytes()).collect();
        for y in 0..40u32 {
            let (ok, _) = self.send_cmd(CMD_SHOWPIC, &row, Some(y * 4))?;
            if !ok { return Ok(false); }
        }
        Ok(true)
    }

    pub fn lcd_picture(&mut self, image_data: &[u8]) -> Result<bool> {
        self.send_lcd(image_data, 128 * 160 * 2, 40, 0)
    }

    pub fn lcd_picture_bottom(&mut self, image_data: &[u8]) -> Result<bool> {
        self.send_lcd(image_data, 128 * 80 * 2, 20, 80)
    }

    fn send_lcd(&mut self, data: &[u8], expected_len: usize, rows: u32, y_offset: u32) -> Result<bool> {
        if data.len() != expected_len {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "invalid image data size",
            ).into());
        }
        for y in 0..rows {
            let chunk = &data[(y as usize * 1024)..((y as usize + 1) * 1024)];
            let (ok, _) = self.send_cmd(CMD_SHOWPIC, chunk, Some(y_offset + y * 4))?;
            if !ok { return Ok(false); }
        }
        Ok(true)
    }
}

impl Drop for KmboxNet {
    fn drop(&mut self) {
        let _ = self.left(false);
        let _ = self.right(false);
        let _ = self.middle(false);
        let _ = self.unmask_all();
    }
}

fn hex_decode(s: &str) -> std::result::Result<Vec<u8>, ()> {
    if s.len() % 2 != 0 { return Err(()); }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).map_err(|_| ()))
        .collect()
}

fn rand_u32() -> u32 {
    use std::collections::hash_map::RandomState;
    use std::hash::{BuildHasher, Hasher};
    RandomState::new().build_hasher().finish() as u32
}
