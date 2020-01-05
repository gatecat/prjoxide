use std::io::Result;
use std::io::Write;

pub struct BBAWriter<'a> {
    out: &'a mut dyn Write,
}

impl<'a> BBAWriter<'a> {
    pub fn new(out: &mut dyn Write) -> BBAWriter {
        BBAWriter { out }
    }
    pub fn u8_val(&mut self, val: u8) -> Result<()> {
        writeln!(&mut self.out, "u8 {}", val)?;
        Ok(())
    }
    pub fn u16_val(&mut self, val: u16) -> Result<()> {
        writeln!(&mut self.out, "u16 {}", val)?;
        Ok(())
    }
    pub fn u32_val(&mut self, val: u32) -> Result<()> {
        writeln!(&mut self.out, "u32 {}", val)?;
        Ok(())
    }
    pub fn pre(&mut self, s: &str) -> Result<()> {
        writeln!(&mut self.out, "pre {}", s)?;
        Ok(())
    }
    pub fn post(&mut self, s: &str) -> Result<()> {
        writeln!(&mut self.out, "post {}", s)?;
        Ok(())
    }
    pub fn push(&mut self, s: &str) -> Result<()> {
        writeln!(&mut self.out, "push {}", s)?;
        Ok(())
    }
}
