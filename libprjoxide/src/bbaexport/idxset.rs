use std::collections::HashMap;
use std::cmp::Eq;
use std::hash::Hash;

pub struct IndexedSet<T: Eq + Hash + Clone> {
	keys: Vec<T>,
	key_to_index: HashMap<T, usize>
}

impl<T: Eq + Hash + Clone> IndexedSet<T> {
	pub fn new() -> IndexedSet<T> {
		IndexedSet::<T> {
			keys: Vec::new(),
			key_to_index: HashMap::new()
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
}
