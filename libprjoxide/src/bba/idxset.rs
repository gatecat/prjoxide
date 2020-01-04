use std::cmp::Eq;
use std::collections::HashMap;
use std::hash::Hash;

pub struct IndexedSet<T: Eq + Hash + Clone> {
    keys: Vec<T>,
    key_to_index: HashMap<T, usize>,
}

impl<T: Eq + Hash + Clone> IndexedSet<T> {
    pub fn new() -> IndexedSet<T> {
        IndexedSet::<T> {
            keys: Vec::new(),
            key_to_index: HashMap::new(),
        }
    }

    pub fn add(&mut self, key: &T) -> usize {
        match self.key_to_index.get(key) {
            Some(k) => *k,
            None => {
                let index = self.keys.len();
                self.keys.push(key.clone());
                self.key_to_index.insert(key.clone(), index);
                return index;
            }
        }
    }

    pub fn get_index(&self, key: &T) -> Option<usize> {
        self.key_to_index.get(key).cloned()
    }

    pub fn key(&self, index: usize) -> &T {
        &self.keys[index]
    }

    pub fn iter(&self) -> std::slice::Iter<T> {
        self.keys.iter()
    }
}

pub struct IndexedMap<Key: Eq + Hash + Clone, Value> {
    data: Vec<(Key, Value)>,
    key_to_index: HashMap<Key, usize>,
}

impl<Key: Eq + Hash + Clone, Value> IndexedMap<Key, Value> {
    pub fn new() -> IndexedMap<Key, Value> {
        IndexedMap::<Key, Value> {
            data: Vec::new(),
            key_to_index: HashMap::new(),
        }
    }

    pub fn add(&mut self, key: &Key, value: Value) -> usize {
        match self.key_to_index.get(key) {
            Some(k) => *k,
            None => {
                let index = self.data.len();
                self.data.push((key.clone(), value));
                self.key_to_index.insert(key.clone(), index);
                return index;
            }
        }
    }

    pub fn get_index(&self, key: &Key) -> Option<usize> {
        self.key_to_index.get(key).cloned()
    }

    pub fn key(&self, index: usize) -> &Key {
        &self.data[index].0
    }

    pub fn value(&self, index: usize) -> &Value {
        &self.data[index].1
    }

    pub fn value_mut(&mut self, index: usize) -> &mut Value {
        &mut self.data[index].1
    }

    pub fn iter(&self) -> std::slice::Iter<(Key, Value)> {
        self.data.iter()
    }
}
