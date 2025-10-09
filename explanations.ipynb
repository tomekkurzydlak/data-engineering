lorem ipsum bla bla bah
this i s not a code
use anyhow::Result;
use chrono::{DateTime, Utc};
use clap::Parser;
use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use tracing::{error, info};
// use pdf::file::Cache;
// use crate::object::{PlainRef, Resolve, Object, NoResolve, ObjectWrite, Updater, DeepClone, Cloner};
// use pdf::object::PlainRef;

// use pdf::any::AnySync;
use pdf::file::FileOptions;
// use pdf::object::{Resolve, Page};
// use pdf::content::{Op};
// use pdf::primitive::Primitive;
use pdf::primitive::Date;

#[derive(Parser, Debug)]
#[command(author, version, about = "Extract text and metadata from PDFs (pure Rust)", long_about = None)]
pub struct Args {
    #[arg(long, help = "Ścieżki do plików PDF, oddzielone przecinkami")]
    pub inputs: String,

    #[arg(long, default_value = "./out/meta")]
    pub meta_out: PathBuf,

    #[arg(long, default_value = "./out/data")]
    pub data_out: PathBuf,
}

#[derive(Serialize)]
struct PdfMetadata {
    title: Option<String>,
    author: Option<String>,
    subject: Option<String>,
    keywords: Option<String>,
    creator: Option<String>,
    producer: Option<String>,
    creation_date: Option<String>,
    modification_date: Option<String>,
    page_count: usize,
}

#[derive(Serialize)]
struct PdfPayload {
    file_path: String,
    file_name: String,
    extracted_at_utc: DateTime<Utc>,
    text_chars: usize,
    has_text_layer: bool,
    metadata: PdfMetadata,
}

type PdfFile = pdf::file::File<
    Vec<u8>,
    std::sync::Arc<
        pdf::file::SyncCache<
            pdf::object::PlainRef,
            pdf::error::Result<pdf::any::AnySync, std::sync::Arc<pdf::error::PdfError>>
        >
    >,
    std::sync::Arc<
        pdf::file::SyncCache<
            pdf::object::PlainRef,
            pdf::error::Result<std::sync::Arc<[u8]>, std::sync::Arc<pdf::error::PdfError>>
        >
    >,
    pdf::file::NoLog,
>;


fn main() -> Result<()> {
    tracing_subscriber::fmt().init();

    let args = Args::parse();
    fs::create_dir_all(&args.meta_out)?;
    fs::create_dir_all(&args.data_out)?;

    for input_path in args.inputs.split(',').map(str::trim).filter(|s| !s.is_empty()) {
        match process_pdf(input_path, &args) {
            Ok(_) => info!("Processed {input_path}"),
            Err(err) => error!("Error processing {input_path}: {err:?}"),
        }
    }

    Ok(())
}

fn process_pdf(path_str: &str, args: &Args) -> Result<()> {
    let path = Path::new(path_str);
    let file = FileOptions::cached().open(path)?;
    // let resolver = file.resolver();
    // let text = extract_text_from_pages(&file)?;
    let info = file.trailer.info_dict.as_ref();

    let extract_date = |opt: Option<Date>| {
        opt.map(|d| format!("{:?}", d)) // Date doesn't implement Display
    };

    let meta = PdfMetadata {
        title: info.and_then(|i| i.title.as_ref()).map(|s| s.to_string_lossy()),
        author: info.and_then(|i| i.author.as_ref()).map(|s| s.to_string_lossy()),
        subject: info.and_then(|i| i.subject.as_ref()).map(|s| s.to_string_lossy()),
        keywords: info.and_then(|i| i.keywords.as_ref()).map(|s| s.to_string_lossy()),
        creator: info.and_then(|i| i.creator.as_ref()).map(|s| s.to_string_lossy()),
        producer: info.and_then(|i| i.producer.as_ref()).map(|s| s.to_string_lossy()),
        creation_date: extract_date(info.and_then(|i| i.creation_date.clone())),
        modification_date: extract_date(info.and_then(|i| i.mod_date.clone())),
        page_count: file.pages().count(),
    };

    let text = extract_text_from_pages(&file)?;

    let file_name = path.file_name().unwrap().to_string_lossy().into_owned();

    let payload = PdfPayload {
        file_path: path.canonicalize()?.display().to_string(),
        file_name: file_name.clone(),
        extracted_at_utc: Utc::now(),
        text_chars: text.chars().count(),
        has_text_layer: !text.trim().is_empty(),
        metadata: meta,
    };

    let json_path = args.meta_out.join(format!("{}.json", sanitize_stem(&file_name)));
    fs::write(&json_path, serde_json::to_vec_pretty(&payload)?)?;

    let md_path = args.data_out.join(format!("{}.md", sanitize_stem(&file_name)));
    let mut f = fs::File::create(&md_path)?;
    writeln!(f, "# {}\n", file_name)?;
    writeln!(f, "<!-- generated at {} UTC -->\n", Utc::now())?;
    f.write_all(text.as_bytes())?;

    Ok(())
}
fn extract_text_from_pages(file: &PdfFile) -> Result<String> {

// fn extract_text_from_pages(
//     file: &pdf::file::File<
//         Vec<u8>,
//         std::sync::Arc<pdf::file::SyncCache<pdf::object::PlainRef, pdf::error::Result<AnySync>>>,
//         std::sync::Arc<pdf::file::SyncCache<pdf::object::PlainRef, pdf::error::Result<std::sync::Arc<[u8]>>>>,
//         pdf::file::NoLog,
//     >
// ) -> Result<String> {
    let mut out = String::new();

    for page_res in file.pages() {
        let page = page_res?;
        if let Some(content) = &page.contents {
            let ops = content.operations(&file.resolver())?;

            // let ops = content.operations(file)?;  // file implements Resolve
            for op in ops {
                match op {
                    pdf::content::Op::TextDraw { text } => {
                        out.push_str(&text.to_string_lossy());
                        out.push('\n');
                    }
                    pdf::content::Op::TextDrawAdjusted { array } => {
                        for item in array {
                            match item {
                                pdf::content::TextDrawAdjusted::Text(t) => {
                                    out.push_str(&t.to_string_lossy())
                                }
                                pdf::content::TextDrawAdjusted::Spacing(sp) if sp > 50.0 => out.push(' '),
                                _ => {}
                            }
                        }
                        out.push('\n');
                    }
                    _ => {}
                }
            }
        }
    }

    Ok(out)
}


fn sanitize_stem(name: &str) -> String {
    name.rsplit_once('.')
        .map(|(s, _)| s)
        .unwrap_or(name)
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '-' || c == '_' { c } else { '-' })
        .collect()
}
