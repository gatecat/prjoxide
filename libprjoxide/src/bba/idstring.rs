use std::collections::HashMap;

pub struct IdStringDB {
    strings: Vec<String>,
    id_to_string: HashMap<String, usize>,
}

impl IdStringDB {
    pub fn new() -> IdStringDB {
        let mut db = IdStringDB {
            strings: vec!["".to_string()],
            id_to_string: HashMap::new(),
        };
        db.id_to_string.insert("".to_string(), 0);
        db
    }

    pub fn id(&mut self, id: &str) -> usize {
        match self.id_to_string.get(id) {
            Some(k) => *k,
            None => {
                let index = self.strings.len();
                self.strings.push(id.to_string());
                self.id_to_string.insert(id.to_string(), index);
                return index;
            }
        }
    }

    pub fn get_id(&self, id: &str) -> Option<usize> {
        self.id_to_string.get(id).cloned()
    }

    pub fn str(&self, index: usize) -> &str {
        &self.strings[index]
    }
}
