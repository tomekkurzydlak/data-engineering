plik zawierajacy informacje w rybie tekstowym:
--
use anyhow::Result;
use chrono::{DateTime, Utc};
use clap::Parser;
use lopdf::Document;
use pdf_extract::extract_text_from_mem;
use serde::Serialize;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use tracing::{error, info};
use encoding_rs::{UTF_16BE, UTF_16LE};

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

    // Read the PDF file
    let pdf_bytes = fs::read(path)?;

    // Load document with lopdf for metadata extraction
    let doc = Document::load_mem(&pdf_bytes)?;

    // Extract metadata using lopdf
    let meta = extract_metadata(&doc)?;

    // Extract text using pdf-extract
    let text = extract_text_from_mem(&pdf_bytes)?;

    let file_name = path.file_name()
        .ok_or_else(|| anyhow::anyhow!("Invalid file path"))?
        .to_string_lossy()
        .into_owned();

    let payload = PdfPayload {
        file_path: path.canonicalize()?.display().to_string(),
        file_name: file_name.clone(),
        extracted_at_utc: Utc::now(),
        text_chars: text.chars().count(),
        has_text_layer: !text.trim().is_empty(),
        metadata: meta,
    };

    // Save JSON metadata
    let json_path = args.meta_out.join(format!("{}.json", sanitize_stem(&file_name)));
    fs::write(&json_path, serde_json::to_vec_pretty(&payload)?)?;

    // Save text as Markdown
    let md_path = args.data_out.join(format!("{}.md", sanitize_stem(&file_name)));
    let mut f = fs::File::create(&md_path)?;
    writeln!(f, "# {}\n", file_name)?;
    writeln!(f, "<!-- generated at {} UTC -->\n", Utc::now())?;

    // Process text for better markdown formatting
    let formatted_text = format_text_for_markdown(&text);
    f.write_all(formatted_text.as_bytes())?;

    Ok(())
}

fn extract_metadata(doc: &Document) -> Result<PdfMetadata> {
    // Wersja 0.38: doc.trailer to już Dictionary, nie trzeba rozpakowywać
    let trailer = &doc.trailer;

    // Pobierz obiekt /Info
    let info_obj = trailer.get(b"Info")?;

    // Rozwiąż referencję lub wyciągnij bezpośrednio słownik
    let info_dict = match info_obj {
        lopdf::Object::Reference(oid) => match doc.get_object(*oid)? {
            lopdf::Object::Dictionary(ref dict) => Some(dict.clone()),
            _ => None,
        },
        lopdf::Object::Dictionary(ref dict) => Some(dict.clone()),
        _ => None,
    };

    let get_string_from_dict = |dict: &lopdf::Dictionary, key: &[u8]| -> Option<String> {
        match dict.get(key) {
            Ok(lopdf::Object::String(ref bytes, _)) => {
                if bytes.starts_with(&[0xFE, 0xFF]) {
                    // UTF-16BE z BOM-em FE FF
                    let (cow, _, _) = UTF_16BE.decode(&bytes[2..]);
                    Some(cow.into_owned())
                } else if bytes.starts_with(&[0xFF, 0xFE]) {
                    // UTF-16LE z BOM-em FF FE
                    let (cow, _, _) = UTF_16LE.decode(&bytes[2..]);
                    Some(cow.into_owned())
                } else {
                    Some(String::from_utf8_lossy(&bytes).into_owned())
                }
            }
            Ok(lopdf::Object::Name(ref bytes)) => Some(String::from_utf8_lossy(&bytes).into_owned()),
            _ => None,
        }
    };


    let get_date_from_dict = |dict: &lopdf::Dictionary, key: &[u8]| -> Option<String> {
        match dict.get(key) {
            Ok(lopdf::Object::String(ref bytes, _)) => {
                let date_str = String::from_utf8_lossy(&bytes);
                Some(parse_pdf_date(&date_str).unwrap_or_else(|| date_str.into_owned()))
            }
            _ => None,
        }
    };

    let metadata = if let Some(info) = info_dict {
        PdfMetadata {
            title: get_string_from_dict(&info, b"Title"),
            author: get_string_from_dict(&info, b"Author"),
            subject: get_string_from_dict(&info, b"Subject"),
            keywords: get_string_from_dict(&info, b"Keywords"),
            creator: get_string_from_dict(&info, b"Creator"),
            producer: get_string_from_dict(&info, b"Producer"),
            creation_date: get_date_from_dict(&info, b"CreationDate"),
            modification_date: get_date_from_dict(&info, b"ModDate"),
            page_count: doc.get_pages().len(),
        }
    } else {
        PdfMetadata {
            title: None,
            author: None,
            subject: None,
            keywords: None,
            creator: None,
            producer: None,
            creation_date: None,
            modification_date: None,
            page_count: doc.get_pages().len(),
        }
    };

    Ok(metadata)
}



fn parse_pdf_date(date_str: &str) -> Option<String> {
    // PDF dates are typically in format: D:YYYYMMDDHHmmSSOHH'mm
    // Example: D:20231225120000+01'00
    if !date_str.starts_with("D:") || date_str.len() < 16 {
        return None;
    }

    let clean_date = &date_str[2..];

    // Try to parse basic components
    let year = clean_date.get(0..4)?;
    let month = clean_date.get(4..6)?;
    let day = clean_date.get(6..8)?;
    let hour = clean_date.get(8..10).unwrap_or("00");
    let minute = clean_date.get(10..12).unwrap_or("00");
    let second = clean_date.get(12..14).unwrap_or("00");

    Some(format!("{}-{}-{} {}:{}:{}", year, month, day, hour, minute, second))
}

fn format_text_for_markdown(text: &str) -> String {
    let mut result = String::new();
    let mut last_was_empty = false;

    for line in text.lines() {
        let trimmed = line.trim();

        if trimmed.is_empty() {
            if !last_was_empty {
                result.push_str("\n\n");
                last_was_empty = true;
            }
        } else {
            // Check if line looks like a heading (all caps, short)
            if trimmed.len() < 80 && trimmed.chars().filter(|c| c.is_alphabetic()).all(|c| c.is_uppercase()) {
                result.push_str(&format!("## {}\n\n", trimmed));
            } else {
                result.push_str(trimmed);
                result.push('\n');
            }
            last_was_empty = false;
        }
    }

    // Clean up multiple consecutive newlines
    let mut final_result = String::new();
    let mut newline_count = 0;

    for ch in result.chars() {
        if ch == '\n' {
            newline_count += 1;
            if newline_count <= 2 {
                final_result.push(ch);
            }
        } else {
            newline_count = 0;
            final_result.push(ch);
        }
    }

    final_result
}

fn sanitize_stem(name: &str) -> String {
    name.rsplit_once('.')
        .map(|(s, _)| s)
        .unwrap_or(name)
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '-' || c == '_' { c } else { '-' })
        .collect()
}
