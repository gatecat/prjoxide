use std::collections::HashMap;

use crate::bba::bbastruct::BBAStructs;
use std::fs::File;
use std::io::{prelude::*, BufReader};

#[derive(PartialEq, Eq, PartialOrd, Ord, Hash, Clone, Copy)]
pub struct IdString(usize);

impl IdString {
    pub fn val(&self) -> usize {
        return self.0;
    }
}

pub struct IdStringDB {
    strings: Vec<String>,
    string_to_id: HashMap<String, IdString>,
    const_ids_count: usize,
}

impl IdStringDB {
    pub fn new() -> IdStringDB {
        let mut db = IdStringDB {
            strings: vec!["".to_string()],
            string_to_id: HashMap::new(),
            const_ids_count: 1,
        };
        db.string_to_id.insert("".to_string(), IdString(0));
        db
    }

    // Setup from a nextpnr constids file
    pub fn from_constids(filename: &str) -> std::io::Result<IdStringDB> {
        let mut ids = IdStringDB::new();
        let file = File::open(filename)?;
        let reader = BufReader::new(file);
        for line in reader.lines() {
            let l = line?;
            if l.len() < 3 || &l[0..2] != "X(" {
                continue;
            }
            let end_pos = l.rfind(')').unwrap();
            let constid = &l[2..end_pos];
            ids.id(constid);
        }
        ids.const_ids_count = ids.strings.len();
        Ok(ids)
    }

    pub fn write_bba(&self, out: &mut BBAStructs) -> std::io::Result<()> {
        out.string_list("bba_idstrings", &self.strings[self.const_ids_count..])?;
        out.list_begin("id_db")?;
        out.id_string_db(
            self.const_ids_count,
            self.strings.len() - self.const_ids_count,
            "bba_idstrings",
        )?;
        Ok(())
    }

    pub fn id(&mut self, id: &str) -> IdString {
        match self.string_to_id.get(id) {
            Some(k) => *k,
            None => {
                let index = self.strings.len();
                self.strings.push(id.to_string());
                self.string_to_id.insert(id.to_string(), IdString(index));
                return IdString(index);
            }
        }
    }

    pub fn get_id(&self, id: &str) -> Option<IdString> {
        self.string_to_id.get(id).cloned()
    }

    pub fn str(&self, index: IdString) -> &str {
        &self.strings[index.0]
    }

    pub fn len(&self) -> usize {
        self.strings.len()
    }
    pub fn idx_str(&self, index: usize) -> &str {
        &self.strings[index]
    }
}
