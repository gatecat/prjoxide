use pulldown_cmark::{html, Options, Parser};
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

pub fn md_to_html(md: &str) -> String {
    let mut options = Options::empty();
    options.insert(Options::ENABLE_STRIKETHROUGH);
    options.insert(Options::ENABLE_TABLES);
    let parser = Parser::new_ext(md, options);

    // Write to String buffer.
    let mut html_output = String::new();
    html::push_html(&mut html_output, parser);
    html_output
}

pub fn md_file_to_html(filename: &str) -> String {
    let mut preproc = String::new();
    preprocess(filename, &mut preproc);
    md_to_html(&preproc)
}
