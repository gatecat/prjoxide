use std::collections::HashMap;

#[derive(PartialEq, Eq, PartialOrd, Ord, Hash, Clone, Copy)]
pub struct IdString(usize);

pub struct IdStringDB {
    strings: Vec<String>,
    string_to_id: HashMap<String, IdString>,
}

impl IdStringDB {
    pub fn new() -> IdStringDB {
        let mut db = IdStringDB {
            strings: vec!["".to_string()],
            string_to_id: HashMap::new(),
        };
        db.string_to_id.insert("".to_string(), IdString(0));
        db
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
}
