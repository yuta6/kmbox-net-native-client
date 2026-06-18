#[derive(Clone, Debug, Default)]
pub struct HardMouse {
    pub report_id: u8,
    pub buttons: u8,
    pub x: i16,
    pub y: i16,
    pub wheel: i16,
}

impl HardMouse {
    pub fn left(&self) -> bool { self.buttons & 0x01 != 0 }
    pub fn right(&self) -> bool { self.buttons & 0x02 != 0 }
    pub fn middle(&self) -> bool { self.buttons & 0x04 != 0 }
    pub fn side1(&self) -> bool { self.buttons & 0x08 != 0 }
    pub fn side2(&self) -> bool { self.buttons & 0x10 != 0 }
}

#[derive(Clone, Debug, Default)]
pub struct HardKeyboard {
    pub report_id: u8,
    pub buttons: u8,
    pub data: [u8; 10],
}

impl HardKeyboard {
    pub fn is_pressed(&self, vkey: u8) -> bool {
        if (0xE0..=0xE7).contains(&vkey) {
            self.buttons & (1 << (vkey - 0xE0)) != 0
        } else {
            self.data.contains(&vkey)
        }
    }
}

pub struct MonitorPacket {
    pub mouse: HardMouse,
    pub keyboard: HardKeyboard,
}

impl MonitorPacket {
    pub fn parse(data: &[u8]) -> Option<Self> {
        if data.len() < 20 {
            return None;
        }
        let mouse = HardMouse {
            report_id: data[0],
            buttons: data[1],
            x: i16::from_le_bytes([data[2], data[3]]),
            y: i16::from_le_bytes([data[4], data[5]]),
            wheel: i16::from_le_bytes([data[6], data[7]]),
        };
        let mut kb_data = [0u8; 10];
        kb_data.copy_from_slice(&data[10..20]);
        let keyboard = HardKeyboard {
            report_id: data[8],
            buttons: data[9],
            data: kb_data,
        };
        Some(Self { mouse, keyboard })
    }
}
