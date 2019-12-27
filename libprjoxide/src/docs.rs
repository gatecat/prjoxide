use std::fs::File;
use std::io::prelude::*;
use std::io::BufReader;
use std::path::Path;

fn preprocess(filename: &str, out: &mut String) {
    let file = File::open(filename).unwrap();
    let reader = BufReader::new(file);

    for line in reader.lines().map(Result::unwrap) {
        if line.starts_with(".include ") {
            let relpath = &line[9..];
            let incpath = Path::new(filename).parent().unwrap().join(relpath);
            preprocess(incpath.to_str().unwrap(), out);
        } else {
            out.push_str(&line);
            out.push('\n');
        }
    }
}
