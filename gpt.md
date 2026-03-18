#[derive(Clone, Debug)]
pub struct AuthConfig {
    pub mode: AuthMode,
    pub api_keys: Vec<String>,
}

#[derive(Clone, Debug)]
pub struct OnnxConfig {
    pub model_path: String,
    pub tokenizer_path: String,
    pub max_len: usize,
    pub intra_threads: usize,
    pub inter_threads: usize,
    pub session_pool_size: usize,
    pub chunk_words: usize,
    pub chunk_overlap_words: usize,
    pub max_chunks: usize,
}

#[derive(Clone, Debug)]
pub enum PerplexityMode {
    LocalPseudo,
    Http,
}

#[derive(Clone, Debug)]
pub struct PerplexityConfig {
    pub mode: PerplexityMode,
    pub endpoint: Option<String>,
    pub gateway_header: Option<String>,
    pub api_key: Option<String>,
    pub model: String,
    pub timeout_ms: u64,
    pub chunk_tokens_estimate: usize,
    pub chunk_overlap_tokens_estimate: usize,
    pub chars_per_token_estimate: f64,
    pub max_chunks: usize,
}

#[derive(Clone, Debug)]
pub struct AppConfig {
    pub env: String,
    pub http: HttpConfig,
    pub auth: AuthConfig,
    pub onnx: OnnxConfig,
    pub batch_parallelism: usize,
    pub score_weights: ScoreWeights,
    pub perplexity: PerplexityConfig,
}

impl AppConfig {
    pub fn from_env() -> anyhow::Result<Self> {
        let score_weights = ScoreWeights {
            coverage: env_f64("DQI_WEIGHT_COVERAGE", 0.30),
            readability: env_f64("DQI_WEIGHT_READABILITY", 0.0),
            completeness: env_f64("DQI_WEIGHT_COMPLETENESS", 0.0),
            structure: env_f64("DQI_WEIGHT_STRUCTURE", 0.25),
            noise: env_f64("DQI_WEIGHT_NOISE", 0.20),
            info_density: env_f64("DQI_WEIGHT_INFO_DENSITY", 0.25),
            semantic_coherence: env_f64("DQI_WEIGHT_SEMANTIC_COHERENCE", 0.0),
            value: env_f64("DQI_WEIGHT_VALUE", 0.0),
            perplexity: env_f64("DQI_WEIGHT_PERPLEXITY", 0.0),
            conversion_quality: env_f64("DQI_WEIGHT_CONVERSION_QUALITY", 0.0),
        }
        .normalized();

        let perplexity_mode = match env::var("PERPLEXITY_MODE")
            .unwrap_or_else(|_| "local_pseudo".to_string())
            .to_lowercase()
            .as_str()
        {
            "http" => PerplexityMode::Http,
            _ => PerplexityMode::LocalPseudo,
        };

        let auth_mode = match env::var("AUTH_MODE")
            .unwrap_or_else(|_| "no_auth".to_string())
            .to_lowercase()
            .as_str()
        {
            "api_key" => AuthMode::ApiKey,
            _ => AuthMode::NoAuth,
        };

        let api_keys = env::var("API_KEYS")
            .unwrap_or_default()
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(ToString::to_string)
            .collect::<Vec<_>>();
        if matches!(auth_mode, AuthMode::ApiKey) && api_keys.is_empty() {
            anyhow::bail!("AUTH_MODE=api_key requires API_KEYS");
        }

        let config = Self {
            env: env::var("APP_ENV").unwrap_or_else(|_| "dev".to_string()),
            http: HttpConfig {
                bind_host: env::var("HTTP_BIND_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
                bind_port: env_u16("HTTP_BIND_PORT", 8080),
            },
            auth: AuthConfig {
                mode: auth_mode,
                api_keys,
            },
            onnx: OnnxConfig {
                model_path: env::var("ONNX_MODEL_PATH")
                    .unwrap_or_else(|_| "models/ner_onnx_pl_herbert/model.onnx".to_string()),
                tokenizer_path: env::var("ONNX_TOKENIZER_PATH")
                    .unwrap_or_else(|_| "models/ner_onnx_pl_herbert/tokenizer.json".to_string()),
                max_len: env_usize("ONNX_MAX_LEN", 256),
                intra_threads: env_usize("ONNX_INTRA_THREADS", 1),
                inter_threads: env_usize("ONNX_INTER_THREADS", 1),
                session_pool_size: env_usize("ONNX_SESSION_POOL_SIZE", 2),
                chunk_words: env_usize("ONNX_CHUNK_WORDS", 220).max(1),
                chunk_overlap_words: env_usize("ONNX_CHUNK_OVERLAP_WORDS", 40),
                max_chunks: env_usize("ONNX_MAX_CHUNKS", 0),
            },
            batch_parallelism: env_usize("BATCH_PARALLELISM", 4).max(1),
            score_weights,
            perplexity: PerplexityConfig {
                mode: perplexity_mode,
                endpoint: env::var("PERPLEXITY_HTTP_ENDPOINT").ok(),
                gateway_header: env::var("PERPLEXITY_GATEWAY_HEADER").ok(),
                api_key: env::var("PERPLEXITY_HTTP_API_KEY").ok(),
                model: env::var("PERPLEXITY_MODEL").unwrap_or_else(|_| "gpt-oss-120b".to_string()),
                timeout_ms: env_u64("PERPLEXITY_TIMEOUT_MS", 5000),
                chunk_tokens_estimate: env_usize("PERPLEXITY_CHUNK_TOKENS", 1800).max(1),
                chunk_overlap_tokens_estimate: env_usize("PERPLEXITY_CHUNK_OVERLAP_TOKENS", 180),
                chars_per_token_estimate: env_f64("PERPLEXITY_CHARS_PER_TOKEN", 3.2),
                max_chunks: env_usize("PERPLEXITY_MAX_CHUNKS", 0),
            },
        };

        if matches!(config.perplexity.mode, PerplexityMode::Http)
            && config
                .perplexity
                .gateway_header
                .as_deref()
                .unwrap_or("")
                .is_empty()
        {
            anyhow::bail!("PERPLEXITY_GATEWAY_HEADER is required when PERPLEXITY_MODE=http");
        }

        Ok(config)
    }
}

fn env_u16(key: &str, default: u16) -> u16 {
    env::var(key)
        .ok()
        .and_then(|v| v.parse::<u16>().ok())
        .unwrap_or(default)
}

fn env_u64(key: &str, default: u64) -> u64 {
    env::var(key)
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(default)
}

fn env_usize(key: &str, default: usize) -> usize {
    env::var(key)
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(default)
}

fn env_f64(key: &str, default: f64) -> f64 {
    env::var(key)
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
        .unwrap_or(default)
}


===


use actix_service::{Service, Transform};
use actix_web::body::EitherBody;
use actix_web::dev::{ServiceRequest, ServiceResponse};
use actix_web::{Error, HttpResponse};
use std::collections::HashSet;
use std::future::{Future, Ready, ready};
use std::pin::Pin;
use std::rc::Rc;
use std::task::{Context, Poll};

#[derive(Clone)]
pub struct ApiKeyAuth {
    keys: Rc<HashSet<String>>,
}

impl ApiKeyAuth {
    pub fn new(api_keys: Vec<String>) -> Self {
        Self {
            keys: Rc::new(api_keys.into_iter().collect()),
        }
    }

    fn is_enabled(&self) -> bool {
        !self.keys.is_empty()
    }
}

impl<S, B> Transform<S, ServiceRequest> for ApiKeyAuth
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<EitherBody<B>>;
    type Error = Error;
    type InitError = ();
    type Transform = ApiKeyAuthMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(ApiKeyAuthMiddleware {
            service: Rc::new(service),
            keys: self.keys.clone(),
            enabled: self.is_enabled(),
        }))
    }
}

pub struct ApiKeyAuthMiddleware<S> {
    service: Rc<S>,
    keys: Rc<HashSet<String>>,
    enabled: bool,
}

impl<S, B> Service<ServiceRequest> for ApiKeyAuthMiddleware<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<EitherBody<B>>;
    type Error = Error;
    type Future = Pin<Box<dyn Future<Output = Result<Self::Response, Self::Error>>>>;

    fn poll_ready(&self, ctx: &mut Context<'_>) -> Poll<Result<(), Self::Error>> {
        self.service.poll_ready(ctx)
    }

    fn call(&self, req: ServiceRequest) -> Self::Future {
        if !self.enabled {
            let srv = self.service.clone();
            return Box::pin(async move {
                let res = srv.call(req).await?;
                Ok(res.map_into_left_body())
            });
        }

        let provided_key = req
            .headers()
            .get("x-api-key")
            .and_then(|h| h.to_str().ok())
            .map(ToString::to_string);

        if let Some(key) = provided_key
            && self.keys.contains(&key)
        {
            let srv = self.service.clone();
            return Box::pin(async move {
                let res = srv.call(req).await?;
                Ok(res.map_into_left_body())
            });
        }

        Box::pin(async move {
            let response = HttpResponse::Unauthorized().json(serde_json::json!({
                "error": "missing_or_invalid_api_key"
            }));
            Ok(req.into_response(response).map_into_right_body())
        })
    }
}



===


features

use crate::dqi::parser::{BROKEN_LIST_RE, CONTROL_RE, HEADING_RE, LIST_RE};
use crate::dqi::scoring::clamp_0_100;
use once_cell::sync::Lazy;
use regex::Regex;
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashMap, HashSet};

pub type FeatureMap = BTreeMap<String, Value>;

static PARAGRAPH_SPLIT_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\n\s*\n").expect("paragraph split regex"));
static GLUE_TOKEN_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[A-Za-z]{6,}[0-9]{3,}|[a-z]{3,}[A-Z]{3,}").expect("glue token regex")
});

pub fn coverage_features(text: &str, lines: &[String], tokens: &[String]) -> FeatureMap {
    let headings = lines
        .iter()
        .enumerate()
        .filter(|(_, l)| HEADING_RE.is_match(l))
        .map(|(idx, _)| idx)
        .collect::<Vec<_>>();

    let nonempty_line_count = lines.iter().filter(|l| !l.trim().is_empty()).count();

    let paragraphs = PARAGRAPH_SPLIT_RE
        .split(text)
        .filter(|blk| {
            let trimmed = blk.trim();
            !trimmed.is_empty() && !HEADING_RE.is_match(trimmed)
        })
        .count();

    let mut empty_section_count = 0usize;
    for (idx, start) in headings.iter().enumerate() {
        let mut end = lines.len();
        if let Some(next_start) = headings.get(idx + 1) {
            end = *next_start;
        }
        let body = lines[start + 1..end].join("\n");
        if body.trim().is_empty() {
            empty_section_count += 1;
        }
    }

    let section_count = headings.len();

    BTreeMap::from([
        ("char_count".to_string(), json!(text.chars().count())),
        ("word_count".to_string(), json!(tokens.len())),
        (
            "nonempty_line_count".to_string(),
            json!(nonempty_line_count),
        ),
        ("paragraph_count".to_string(), json!(paragraphs)),
        ("heading_count".to_string(), json!(section_count)),
        ("section_count".to_string(), json!(section_count)),
        (
            "empty_section_count".to_string(),
            json!(empty_section_count),
        ),
        (
            "content_line_ratio".to_string(),
            json!(nonempty_line_count as f64 / lines.len().max(1) as f64),
        ),
        (
            "empty_section_ratio".to_string(),
            json!(empty_section_count as f64 / section_count.max(1) as f64),
        ),
    ])
}

pub fn structure_features(text: &str, lines: &[String]) -> FeatureMap {
    let heading_lines = lines
        .iter()
        .filter_map(|l| HEADING_RE.captures(l))
        .collect::<Vec<_>>();

    let paragraph_count = PARAGRAPH_SPLIT_RE
        .split(text)
        .filter(|b| !b.trim().is_empty())
        .count();
    let table_count = lines
        .iter()
        .filter(|l| l.contains('|') && l.matches('|').count() >= 2)
        .count();

    BTreeMap::from([
        ("heading_count".to_string(), json!(heading_lines.len())),
        ("section_count".to_string(), json!(heading_lines.len())),
        ("paragraph_count".to_string(), json!(paragraph_count)),
        (
            "list_count".to_string(),
            json!(lines.iter().filter(|l| LIST_RE.is_match(l)).count()),
        ),
        ("table_count".to_string(), json!(table_count)),
        (
            "broken_heading_count".to_string(),
            json!(
                heading_lines
                    .iter()
                    .filter(|caps| caps
                        .get(2)
                        .map(|m| m.as_str().trim())
                        .unwrap_or("")
                        .is_empty())
                    .count()
            ),
        ),
        (
            "broken_list_marker_count".to_string(),
            json!(lines.iter().filter(|l| BROKEN_LIST_RE.is_match(l)).count()),
        ),
    ])
}

pub fn readability_features(tokens: &[String], sentence_count: usize) -> FeatureMap {
    let avg_sentence_len = tokens.len() as f64 / sentence_count.max(1) as f64;
    let long_word_ratio =
        tokens.iter().filter(|t| t.len() >= 10).count() as f64 / tokens.len().max(1) as f64;

    BTreeMap::from([
        ("sentence_count".to_string(), json!(sentence_count)),
        ("avg_sentence_len".to_string(), json!(avg_sentence_len)),
        ("long_word_ratio".to_string(), json!(long_word_ratio)),
    ])
}

pub fn completeness_features(coverage: &FeatureMap, structure: &FeatureMap) -> FeatureMap {
    let section_count = as_f64(coverage, "section_count");
    let paragraph_count = as_f64(coverage, "paragraph_count");
    let empty_section_ratio = as_f64(coverage, "empty_section_ratio");
    let broken_heading_count = as_f64(structure, "broken_heading_count");

    BTreeMap::from([
        (
            "has_min_sections".to_string(),
            json!(section_count >= 2.0 || paragraph_count >= 3.0),
        ),
        (
            "empty_section_ratio".to_string(),
            json!(empty_section_ratio),
        ),
        (
            "broken_heading_count".to_string(),
            json!(broken_heading_count),
        ),
    ])
}

pub fn noise_features(text: &str, lines: &[String]) -> FeatureMap {
    let tokens = text
        .split_whitespace()
        .map(ToString::to_string)
        .collect::<Vec<_>>();

    let replacement_char_count = text.matches('\u{fffd}').count() + text.matches('�').count();
    let control_char_count = CONTROL_RE.find_iter(text).count();
    let weird_unicode_ratio = text
        .chars()
        .filter(|ch| *ch as u32 > 127 && !ch.is_alphabetic())
        .count() as f64
        / text.chars().count().max(1) as f64;

    let long_token_ratio =
        tokens.iter().filter(|t| t.len() >= 30).count() as f64 / tokens.len().max(1) as f64;
    let punct_count = text
        .chars()
        .filter(|ch| "!?.,;:-_+=*/\\|[]{}()<>~`\"'@#$%^&".contains(*ch))
        .count();

    let mut counter = HashMap::<String, usize>::new();
    for line in lines.iter().map(|s| s.trim()).filter(|l| !l.is_empty()) {
        *counter.entry(line.to_string()).or_default() += 1;
    }
    let repeated_lines = counter
        .values()
        .filter(|v| **v > 1)
        .map(|v| v - 1)
        .sum::<usize>();

    BTreeMap::from([
        (
            "replacement_char_count".to_string(),
            json!(replacement_char_count),
        ),
        ("control_char_count".to_string(), json!(control_char_count)),
        (
            "weird_unicode_ratio".to_string(),
            json!(weird_unicode_ratio),
        ),
        ("long_token_ratio".to_string(), json!(long_token_ratio)),
        (
            "punctuation_ratio".to_string(),
            json!(punct_count as f64 / text.chars().count().max(1) as f64),
        ),
        (
            "digit_ratio".to_string(),
            json!(
                text.chars().filter(|ch| ch.is_ascii_digit()).count() as f64
                    / text.chars().count().max(1) as f64
            ),
        ),
        (
            "glue_like_token_ratio".to_string(),
            json!(
                tokens.iter().filter(|t| GLUE_TOKEN_RE.is_match(t)).count() as f64
                    / tokens.len().max(1) as f64
            ),
        ),
        (
            "repeated_line_ratio".to_string(),
            json!(repeated_lines as f64 / counter.values().sum::<usize>().max(1) as f64),
        ),
    ])
}

pub fn basic_semantic_coherence_features(text: &str, tokens: &[String]) -> FeatureMap {
    let paragraphs = PARAGRAPH_SPLIT_RE
        .split(text)
        .filter(|p| !p.trim().is_empty())
        .collect::<Vec<_>>();

    let mut overlap_sum = 0.0;
    let mut overlap_count = 0usize;
    for w in paragraphs.windows(2) {
        let left = tokenize_to_set(w[0]);
        let right = tokenize_to_set(w[1]);
        let intersection = left.intersection(&right).count();
        let union = left.union(&right).count().max(1);
        overlap_sum += intersection as f64 / union as f64;
        overlap_count += 1;
    }

    let repeated_token_ratio = {
        let mut seen = HashMap::<String, usize>::new();
        for token in tokens {
            *seen.entry(token.to_lowercase()).or_default() += 1;
        }
        seen.values().filter(|count| **count >= 4).sum::<usize>() as f64
            / tokens.len().max(1) as f64
    };

    BTreeMap::from([
        (
            "paragraph_overlap_ratio".to_string(),
            json!(if overlap_count == 0 {
                0.0
            } else {
                overlap_sum / overlap_count as f64
            }),
        ),
        (
            "repeated_token_ratio".to_string(),
            json!(repeated_token_ratio),
        ),
    ])
}

fn tokenize_to_set(text: &str) -> HashSet<String> {
    text.split_whitespace()
        .map(|s| {
            s.trim_matches(|c: char| !c.is_alphanumeric())
                .to_lowercase()
        })
        .filter(|s| !s.is_empty())
        .collect()
}

pub fn coverage_score(features: &FeatureMap) -> f64 {
    let mut score = 100.0;
    let word_count = as_f64(features, "word_count");
    let paragraph_count = as_f64(features, "paragraph_count");
    let content_line_ratio = as_f64(features, "content_line_ratio");
    let empty_section_ratio = as_f64(features, "empty_section_ratio");

    if word_count < 80.0 {
        score -= (80.0 - word_count) * 0.45;
    }
    if paragraph_count < 2.0 {
        score -= (2.0 - paragraph_count) * 10.0;
    }
    if content_line_ratio < 0.55 {
        score -= (0.55 - content_line_ratio) * 85.0;
    }
    score -= empty_section_ratio * 50.0;

    clamp_0_100(score)
}

pub fn structure_score(features: &FeatureMap) -> f64 {
    let mut score = 100.0;
    let heading_count = as_f64(features, "heading_count");
    let broken_heading_count = as_f64(features, "broken_heading_count");
    let broken_list_marker_count = as_f64(features, "broken_list_marker_count");

    if heading_count == 0.0 {
        score -= 35.0;
    }
    score -= broken_heading_count * 10.0;
    score -= broken_list_marker_count * 7.0;

    clamp_0_100(score)
}

pub fn readability_score(features: &FeatureMap) -> f64 {
    let avg_sentence_len = as_f64(features, "avg_sentence_len");
    let long_word_ratio = as_f64(features, "long_word_ratio");

    let sentence_score = (100.0 - (avg_sentence_len - 18.0).abs() * 3.2).max(0.0);
    let long_word_penalty = (long_word_ratio * 80.0).min(35.0);

    clamp_0_100(sentence_score - long_word_penalty)
}

pub fn completeness_score(features: &FeatureMap) -> f64 {
    let has_min_sections = features
        .get("has_min_sections")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    let empty_section_ratio = as_f64(features, "empty_section_ratio");
    let broken_heading_count = as_f64(features, "broken_heading_count");

    let mut score = if has_min_sections { 90.0 } else { 55.0 };
    score -= empty_section_ratio * 45.0;
    score -= broken_heading_count * 8.0;
    clamp_0_100(score)
}

pub fn noise_score(features: &FeatureMap) -> f64 {
    let mut score = 100.0;
    score -= as_f64(features, "replacement_char_count") * 2.0;
    score -= as_f64(features, "control_char_count") * 1.5;
    score -= as_f64(features, "weird_unicode_ratio") * 300.0;
    score -= as_f64(features, "long_token_ratio") * 120.0;
    score -= as_f64(features, "punctuation_ratio") * 80.0;
    score -= as_f64(features, "digit_ratio") * 40.0;
    score -= as_f64(features, "glue_like_token_ratio") * 120.0;
    score -= as_f64(features, "repeated_line_ratio") * 110.0;
    clamp_0_100(score)
}

pub fn info_density_score(features: &FeatureMap) -> f64 {
    let token_count = as_f64(features, "token_count");
    let stopword_ratio = as_f64(features, "stopword_ratio");
    let entity_density = as_f64(features, "entity_density");
    let unique_token_ratio = as_f64(features, "unique_token_ratio");
    let lexical_density_proxy = as_f64(features, "lexical_density_proxy");

    let mut score = 0.0;
    score += (token_count / 20.0).min(30.0);
    score += (unique_token_ratio * 30.0).min(20.0);
    score += (lexical_density_proxy * 25.0).min(20.0);
    score += (entity_density * 250.0).min(20.0);
    score += (10.0 - (stopword_ratio - 0.45).abs() * 25.0).max(0.0);
    clamp_0_100(score)
}

pub fn semantic_coherence_score(features: &FeatureMap) -> f64 {
    let overlap = as_f64(features, "paragraph_overlap_ratio");
    let repeated_tokens = as_f64(features, "repeated_token_ratio");

    clamp_0_100((overlap * 120.0).min(80.0) + (20.0 - (repeated_tokens * 100.0).min(20.0)))
}

pub fn value_score(
    coverage_score: f64,
    completeness_score: f64,
    info_density_score: f64,
    readability_score: f64,
) -> f64 {
    clamp_0_100(
        coverage_score * 0.20
            + completeness_score * 0.30
            + info_density_score * 0.35
            + readability_score * 0.15,
    )
}

fn as_f64(map: &FeatureMap, key: &str) -> f64 {
    map.get(key).and_then(Value::as_f64).unwrap_or_else(|| {
        map.get(key)
            .and_then(Value::as_i64)
            .map(|v| v as f64)
            .unwrap_or(0.0)
    })
}

===

perp

use crate::dqi::scoring::clamp_0_100;
use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashSet;
use std::time::Duration;
use uuid::Uuid;

const PERPLEXITY_SYSTEM_PROMPT: &str = "Jestes asystentem oceny jakosci tekstu. Zwracaj tylko JSON: {\"perplexity\": <float>, \"score_0_100\": <float 0-100>} bez dodatkowego tekstu.";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerplexityResult {
    pub raw: f64,
    pub score_0_100: f64,
}

#[async_trait]
pub trait PerplexityProvider: Send + Sync {
    async fn score(&self, text: &str) -> anyhow::Result<PerplexityResult>;
    fn name(&self) -> &'static str;
}

#[derive(Default)]
pub struct LocalPseudoPerplexityProvider;

#[async_trait]
impl PerplexityProvider for LocalPseudoPerplexityProvider {
    async fn score(&self, text: &str) -> anyhow::Result<PerplexityResult> {
        let tokens = text
            .split_whitespace()
            .map(|token| token.to_lowercase())
            .collect::<Vec<_>>();

        let unique = tokens.iter().collect::<HashSet<_>>().len() as f64;
        let token_count = tokens.len().max(1) as f64;
        let unique_ratio = unique / token_count;

        let avg_token_len =
            tokens.iter().map(|token| token.len() as f64).sum::<f64>() / token_count;

        let raw_ppl =
            ((1.0 - unique_ratio) * 120.0 + (avg_token_len - 5.0).abs() * 3.0 + 12.0).max(1.0);

        let score = clamp_0_100(100.0 - ((raw_ppl - 12.0) * 1.4));
        Ok(PerplexityResult {
            raw: raw_ppl,
            score_0_100: score,
        })
    }

    fn name(&self) -> &'static str {
        "local_pseudo"
    }
}

#[derive(Clone)]
pub struct HttpPerplexityProvider {
    client: Client,
    endpoint: String,
    gateway_header: String,
    api_key: Option<String>,
    model: String,
    user_agent: String,
    chunk_tokens_estimate: usize,
    chunk_overlap_tokens_estimate: usize,
    chars_per_token_estimate: f64,
    max_chunks: usize,
}

impl HttpPerplexityProvider {
    pub fn new(
        endpoint: String,
        gateway_header: String,
        api_key: Option<String>,
        model: String,
        timeout_ms: u64,
        chunk_tokens_estimate: usize,
        chunk_overlap_tokens_estimate: usize,
        chars_per_token_estimate: f64,
        max_chunks: usize,
    ) -> anyhow::Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_millis(timeout_ms))
            .danger_accept_invalid_certs(true)
            .build()?;

        Ok(Self {
            client,
            endpoint,
            gateway_header,
            api_key,
            model,
            user_agent: "dqi-service/1.0".to_string(),
            chunk_tokens_estimate: chunk_tokens_estimate.max(1),
            chunk_overlap_tokens_estimate: chunk_overlap_tokens_estimate
                .min(chunk_tokens_estimate.saturating_sub(1)),
            chars_per_token_estimate: chars_per_token_estimate.max(1.0),
            max_chunks,
        })
    }

    fn build_model_payload<'a>(&'a self, user_content: &'a str) -> Value {
        json!({
            "model": self.model,
            "messages": [
                {"role": "system", "content": PERPLEXITY_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 6500,
            "stream": false
        })
    }

    fn build_user_prompt(&self, text: &str) -> String {
        format!(
            "Wylicz perplexity i score_0_100 dla nastepujacego tekstu:\n\n{}",
            text
        )
    }

    fn apply_headers(&self, request: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        let mut request = request
            .header("accept", "application/json")
            .header("user-agent", &self.user_agent)
            .header("gateway", &self.gateway_header)
            .header("x-request-id", Uuid::new_v4().to_string());

        if let Some(api_key) = &self.api_key {
            request = request.header("authorization", format!("Bearer {api_key}"));
        }

        request
    }

    async fn send_json_request(&self, text: &str) -> anyhow::Result<Value> {
        let payload = self.build_model_payload(&self.build_user_prompt(text));
        let request = self.apply_headers(self.client.post(&self.endpoint).json(&payload));
        let response = request.send().await?.error_for_status()?;
        Ok(response.json::<Value>().await?)
    }

    fn split_text_chunks<'a>(&self, text: &'a str) -> Vec<&'a str> {
        let chars = text.char_indices().collect::<Vec<_>>();
        if chars.is_empty() {
            return vec![text];
        }

        let total_chars = chars.len();
        let mut chunks = Vec::new();
        let mut start_char = 0usize;
        let chunk_chars =
            estimated_chars(self.chunk_tokens_estimate, self.chars_per_token_estimate);
        let overlap_chars = estimated_chars(
            self.chunk_overlap_tokens_estimate,
            self.chars_per_token_estimate,
        )
        .min(chunk_chars.saturating_sub(1));
        let step = chunk_chars.saturating_sub(overlap_chars).max(1);

        while start_char < total_chars {
            let end_char = (start_char + chunk_chars).min(total_chars);
            let start_byte = chars[start_char].0;
            let end_byte = if end_char < total_chars {
                chars[end_char].0
            } else {
                text.len()
            };
            chunks.push(&text[start_byte..end_byte]);

            if self.max_chunks > 0 && chunks.len() >= self.max_chunks {
                break;
            }
            if end_char == total_chars {
                break;
            }
            start_char = start_char.saturating_add(step);
        }

        chunks
    }

    fn parse_gateway_response(&self, response_json: Value) -> anyhow::Result<PerplexityResult> {
        let content = response_json
            .get("choices")
            .and_then(|v| v.get(0))
            .and_then(|v| v.get("message"))
            .and_then(|v| v.get("content"))
            .and_then(Value::as_str)
            .ok_or_else(|| {
                anyhow::anyhow!("missing choices[0].message.content in gateway response")
            })?;

        parse_content_to_result(content)
    }
}

fn estimated_chars(tokens: usize, chars_per_token: f64) -> usize {
    ((tokens as f64) * chars_per_token).round().max(1.0) as usize
}

#[async_trait]
impl PerplexityProvider for HttpPerplexityProvider {
    async fn score(&self, text: &str) -> anyhow::Result<PerplexityResult> {
        let chunks = self.split_text_chunks(text);
        let mut weighted_raw_sum = 0.0;
        let mut weighted_score_sum = 0.0;
        let mut total_weight = 0.0;

        for chunk in chunks {
            let response_json = self.send_json_request(chunk).await?;
            let chunk_result = self.parse_gateway_response(response_json)?;
            let weight = chunk.chars().count().max(1) as f64;
            weighted_raw_sum += chunk_result.raw * weight;
            weighted_score_sum += chunk_result.score_0_100 * weight;
            total_weight += weight;
        }

        if total_weight == 0.0 {
            return Ok(PerplexityResult {
                raw: 0.0,
                score_0_100: 0.0,
            });
        }

        Ok(PerplexityResult {
            raw: weighted_raw_sum / total_weight,
            score_0_100: weighted_score_sum / total_weight,
        })
    }

    fn name(&self) -> &'static str {
        "gateway_http_completions"
    }
}

#[derive(Debug, Deserialize)]
struct PerplexityContentJson {
    perplexity: f64,
    score_0_100: Option<f64>,
}

fn parse_content_to_result(content: &str) -> anyhow::Result<PerplexityResult> {
    let cleaned = content
        .trim()
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim();

    if let Ok(parsed) = serde_json::from_str::<PerplexityContentJson>(cleaned) {
        let score = parsed
            .score_0_100
            .unwrap_or_else(|| clamp_0_100(100.0 - (parsed.perplexity * 0.8)));
        return Ok(PerplexityResult {
            raw: parsed.perplexity,
            score_0_100: score,
        });
    }

    let first_number = cleaned
        .split(|c: char| !(c.is_ascii_digit() || c == '.'))
        .find(|chunk| !chunk.is_empty())
        .and_then(|chunk| chunk.parse::<f64>().ok())
        .ok_or_else(|| anyhow::anyhow!("could not parse perplexity from gateway content"))?;

    Ok(PerplexityResult {
        raw: first_number,
        score_0_100: clamp_0_100(100.0 - (first_number * 0.8)),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn local_pseudo_returns_bounded_score() {
        let provider = LocalPseudoPerplexityProvider;
        let result = provider
            .score("To jest przykładowy dokument o jakości danych i strukturze markdown.")
            .await
            .expect("local pseudo perplexity");
        assert!((0.0..=100.0).contains(&result.score_0_100));
        assert!(result.raw > 0.0);
    }

    #[test]
    fn parses_json_content() {
        let result = parse_content_to_result("{\"perplexity\": 21.5, \"score_0_100\": 80.0}")
            .expect("parse content");
        assert_eq!(result.raw, 21.5);
        assert_eq!(result.score_0_100, 80.0);
    }

    #[test]
    fn splits_text_into_overlapping_chunks() {
        let provider = HttpPerplexityProvider {
            client: Client::builder().build().expect("client"),
            endpoint: "http://localhost".to_string(),
            gateway_header: "g".to_string(),
            api_key: None,
            model: "m".to_string(),
            user_agent: "ua".to_string(),
            chunk_tokens_estimate: 3,
            chunk_overlap_tokens_estimate: 1,
            chars_per_token_estimate: 3.2,
            max_chunks: 0,
        };
        let chunks = provider.split_text_chunks("abcdefghijklmnop");
        assert_eq!(chunks[0], "abcdefghij");
        assert_eq!(chunks[1], "hijklmnop");
    }
}

===

scor

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct ScoreWeights {
    pub coverage: f64,
    pub readability: f64,
    pub completeness: f64,
    pub structure: f64,
    pub noise: f64,
    pub info_density: f64,
    pub semantic_coherence: f64,
    pub value: f64,
    pub perplexity: f64,
    pub conversion_quality: f64,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        Self {
            coverage: 0.30,
            readability: 0.0,
            completeness: 0.0,
            structure: 0.25,
            noise: 0.20,
            info_density: 0.25,
            semantic_coherence: 0.0,
            value: 0.0,
            perplexity: 0.0,
            conversion_quality: 0.0,
        }
    }
}

impl ScoreWeights {
    pub fn normalized(self) -> Self {
        let sum = self.coverage
            + self.readability
            + self.completeness
            + self.structure
            + self.noise
            + self.info_density
            + self.semantic_coherence
            + self.value
            + self.perplexity
            + self.conversion_quality;

        if sum <= 0.0 {
            return Self::default();
        }

        Self {
            coverage: self.coverage / sum,
            readability: self.readability / sum,
            completeness: self.completeness / sum,
            structure: self.structure / sum,
            noise: self.noise / sum,
            info_density: self.info_density / sum,
            semantic_coherence: self.semantic_coherence / sum,
            value: self.value / sum,
            perplexity: self.perplexity / sum,
            conversion_quality: self.conversion_quality / sum,
        }
    }
}

pub fn clamp_0_100(value: f64) -> f64 {
    value.clamp(0.0, 100.0)
}

#[allow(clippy::too_many_arguments)]
pub fn dqi_total(
    coverage_score: f64,
    readability_score: f64,
    completeness_score: f64,
    structure_score: f64,
    noise_score: f64,
    info_density_score: f64,
    semantic_coherence_score: f64,
    value_score: f64,
    perplexity_score: f64,
    conversion_quality_score: f64,
    weights: ScoreWeights,
) -> f64 {
    clamp_0_100(
        coverage_score * weights.coverage
            + readability_score * weights.readability
            + completeness_score * weights.completeness
            + structure_score * weights.structure
            + noise_score * weights.noise
            + info_density_score * weights.info_density
            + semantic_coherence_score * weights.semantic_coherence
            + value_score * weights.value
            + perplexity_score * weights.perplexity
            + conversion_quality_score * weights.conversion_quality,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_weights_sum_to_one() {
        let w = ScoreWeights::default().normalized();
        let sum = w.coverage
            + w.readability
            + w.completeness
            + w.structure
            + w.noise
            + w.info_density
            + w.semantic_coherence
            + w.value
            + w.perplexity
            + w.conversion_quality;
        assert!((sum - 1.0).abs() < 1e-9);
    }

    #[test]
    fn legacy_formula_matches_for_default_weights() {
        let result = dqi_total(
            80.0,
            0.0,
            0.0,
            70.0,
            90.0,
            75.0,
            0.0,
            0.0,
            0.0,
            0.0,
            ScoreWeights::default(),
        );
        assert!((result - (80.0 * 0.30 + 70.0 * 0.25 + 90.0 * 0.20 + 75.0 * 0.25)).abs() < 1e-9);
    }
}


===

semant
use anyhow::{Context, Result};
use once_cell::sync::Lazy;
use ort::session::Session;
use ort::session::builder::GraphOptimizationLevel;
use ort::value::Tensor;
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashSet};
use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;
use tokenizers::Tokenizer;

pub type FeatureMap = BTreeMap<String, Value>;

static STOPWORDS: Lazy<HashSet<&'static str>> = Lazy::new(|| {
    [
        "i", "oraz", "lub", "w", "na", "z", "do", "o", "a", "jest", "są", "to", "od", "dla", "że",
        "jak", "czy", "który", "która", "które", "się", "nie", "tak", "po", "przez", "pod", "nad",
        "bez",
    ]
    .into_iter()
    .collect()
});

pub trait SemanticEngine: Send + Sync {
    fn compute(&self, text: &str, tokens: &[String]) -> (FeatureMap, f64);
    fn warmup(&self);
    fn backend_name(&self) -> &'static str;
}

pub struct OnnxNerSemanticEngine {
    tokenizer: Tokenizer,
    sessions: Arc<Vec<Mutex<Session>>>,
    next_session: AtomicUsize,
    max_len: usize,
    chunk_words: usize,
    chunk_overlap_words: usize,
    max_chunks: usize,
}

impl OnnxNerSemanticEngine {
    pub fn load(
        model_path: &Path,
        tokenizer_path: &Path,
        max_len: usize,
        intra_threads: usize,
        inter_threads: usize,
        session_pool_size: usize,
        chunk_words: usize,
        chunk_overlap_words: usize,
        max_chunks: usize,
    ) -> Result<Self> {
        if session_pool_size == 0 {
            anyhow::bail!("session_pool_size must be >= 1");
        }

        let tokenizer = Tokenizer::from_file(tokenizer_path)
            .map_err(|e| anyhow::anyhow!(e.to_string()))
            .with_context(|| {
                format!("failed to load tokenizer from {}", tokenizer_path.display())
            })?;

        let mut sessions = Vec::with_capacity(session_pool_size);
        for _ in 0..session_pool_size {
            let mut builder = Session::builder()?
                .with_intra_threads(intra_threads)
                .map_err(|e| anyhow::anyhow!(e.to_string()))?
                .with_inter_threads(inter_threads)
                .map_err(|e| anyhow::anyhow!(e.to_string()))?
                .with_optimization_level(GraphOptimizationLevel::All)
                .map_err(|e| anyhow::anyhow!(e.to_string()))?;

            let session = builder
                .commit_from_file(model_path)
                .with_context(|| format!("failed to load ONNX from {}", model_path.display()))?;
            sessions.push(Mutex::new(session));
        }

        Ok(Self {
            tokenizer,
            sessions: Arc::new(sessions),
            next_session: AtomicUsize::new(0),
            max_len,
            chunk_words: chunk_words.max(1),
            chunk_overlap_words: chunk_overlap_words.min(chunk_words.saturating_sub(1)),
            max_chunks,
        })
    }

    fn infer_entity_count(&self, text: &str) -> Result<(usize, usize, f64)> {
        let encoded = self
            .tokenizer
            .encode(text, true)
            .map_err(|e| anyhow::anyhow!(e.to_string()))?;

        let mut input_ids = encoded
            .get_ids()
            .iter()
            .map(|v| *v as i64)
            .collect::<Vec<_>>();
        let mut attention_mask = encoded
            .get_attention_mask()
            .iter()
            .map(|v| *v as i64)
            .collect::<Vec<_>>();
        let mut token_type_ids = encoded
            .get_type_ids()
            .iter()
            .map(|v| *v as i64)
            .collect::<Vec<_>>();

        if input_ids.len() > self.max_len {
            input_ids.truncate(self.max_len);
            attention_mask.truncate(self.max_len);
            token_type_ids.truncate(self.max_len);
        }

        let seq_len = input_ids.len();
        if seq_len == 0 {
            return Ok((0, 0, 0.0));
        }

        let input_ids_tensor = Tensor::<i64>::from_array(([1i64, seq_len as i64], input_ids))?;
        let attention_tensor = Tensor::<i64>::from_array(([1i64, seq_len as i64], attention_mask))?;
        let token_type_tensor =
            Tensor::<i64>::from_array(([1i64, seq_len as i64], token_type_ids))?;

        let t0 = Instant::now();
        let session_idx = self.next_session.fetch_add(1, Ordering::Relaxed) % self.sessions.len();
        let mut session = self.sessions[session_idx]
            .lock()
            .expect("onnx session mutex poisoned");

        let input_count = session.inputs().len();
        let outputs = match input_count {
            2 => session.run(ort::inputs![input_ids_tensor, attention_tensor])?,
            _ => session.run(ort::inputs![
                input_ids_tensor,
                attention_tensor,
                token_type_tensor
            ])?,
        };
        let model_ms = t0.elapsed().as_secs_f64() * 1000.0;

        let logits = outputs[0].try_extract_array::<f32>()?;
        let shape = logits.shape();
        if shape.len() < 3 {
            return Ok((0, seq_len, model_ms));
        }

        let mut entity_tokens = 0usize;
        for i in 0..shape[1] {
            let mut max_idx = 0usize;
            let mut max_val = f32::MIN;
            for label in 0..shape[2] {
                let value = logits[[0, i, label]];
                if value > max_val {
                    max_val = value;
                    max_idx = label;
                }
            }
            if max_idx != 0 {
                entity_tokens += 1;
            }
        }

        Ok((entity_tokens, seq_len, model_ms))
    }

    fn build_chunks<'a>(&self, tokens: &'a [String]) -> Vec<&'a [String]> {
        let step = self
            .chunk_words
            .saturating_sub(self.chunk_overlap_words)
            .max(1);
        let mut chunks = Vec::new();
        let mut start = 0usize;
        while start < tokens.len() {
            let end = (start + self.chunk_words).min(tokens.len());
            chunks.push(&tokens[start..end]);
            if self.max_chunks > 0 && chunks.len() >= self.max_chunks {
                break;
            }
            if end == tokens.len() {
                break;
            }
            start = start.saturating_add(step);
        }
        chunks
    }
}

impl SemanticEngine for OnnxNerSemanticEngine {
    fn compute(&self, text: &str, tokens: &[String]) -> (FeatureMap, f64) {
        let token_count = tokens.len();
        let stopword_count = tokens
            .iter()
            .filter(|t| STOPWORDS.contains(t.to_lowercase().as_str()))
            .count();

        let unique_token_ratio = tokens
            .iter()
            .map(|t| t.to_lowercase())
            .collect::<HashSet<_>>()
            .len() as f64
            / token_count.max(1) as f64;

        let lexical_density_proxy = tokens
            .iter()
            .filter(|t| !STOPWORDS.contains(t.to_lowercase().as_str()))
            .count() as f64
            / token_count.max(1) as f64;

        let chunks = self.build_chunks(tokens);
        let chunk_count = chunks.len();
        let mut entity_count = 0usize;
        let mut model_token_count = 0usize;
        let mut model_ms = 0.0;
        for chunk in chunks {
            let chunk_text = chunk.join(" ");
            if let Ok((entities, seq_len, elapsed_ms)) = self.infer_entity_count(&chunk_text) {
                entity_count += entities;
                model_token_count += seq_len;
                model_ms += elapsed_ms;
            }
        }
        if model_token_count == 0 {
            if let Ok((entities, seq_len, elapsed_ms)) = self.infer_entity_count(text) {
                entity_count = entities;
                model_token_count = seq_len;
                model_ms = elapsed_ms;
            }
        }
        let entity_density = entity_count as f64 / model_token_count.max(1) as f64;

        (
            BTreeMap::from([
                ("token_count".to_string(), json!(token_count)),
                (
                    "stopword_ratio".to_string(),
                    json!(stopword_count as f64 / token_count.max(1) as f64),
                ),
                ("entity_count".to_string(), json!(entity_count)),
                ("entity_density".to_string(), json!(entity_density)),
                ("unique_token_ratio".to_string(), json!(unique_token_ratio)),
                (
                    "lexical_density_proxy".to_string(),
                    json!(lexical_density_proxy),
                ),
                ("ner_chunks_processed".to_string(), json!(chunk_count)),
                (
                    "semantic_backend".to_string(),
                    json!("onnx_token_classification"),
                ),
            ]),
            model_ms,
        )
    }

    fn warmup(&self) {
        let _ = self.compute(
            "To jest test warmupu modelu DQI.",
            &["To".to_string(), "jest".to_string()],
        );
    }

    fn backend_name(&self) -> &'static str {
        "onnx_token_classification"
    }
}

==
serv
use crate::dqi::conversion::evaluate_conversion;
use crate::dqi::features::{
    basic_semantic_coherence_features, completeness_features, completeness_score,
    coverage_features, coverage_score, info_density_score, noise_features, noise_score,
    readability_features, readability_score, semantic_coherence_score, structure_features,
    structure_score, value_score,
};
use crate::dqi::parser::ParsedDoc;
use crate::dqi::perplexity::PerplexityProvider;
use crate::dqi::scoring::{ScoreWeights, dqi_total};
use crate::dqi::semantic_onnx::SemanticEngine;
use crate::dqi::types::{
    BatchScoreRequest, BatchScoreResponse, DocumentScoreResult, ScoreBreakdown, ScoreRequest,
    TimingInfo,
};
use chrono::Utc;
use serde_json::json;
use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Instant;
use tokio::task::JoinSet;
use uuid::Uuid;

#[derive(Clone)]
pub struct DqiService {
    pub semantic_engine: Arc<dyn SemanticEngine>,
    pub perplexity_provider: Arc<dyn PerplexityProvider>,
    pub weights: ScoreWeights,
    pub batch_parallelism: usize,
}

impl DqiService {
    pub async fn score(&self, request: ScoreRequest) -> anyhow::Result<DocumentScoreResult> {
        let request_id = Uuid::new_v4();
        let source = request
            .metadata
            .as_ref()
            .and_then(|m| m.source.clone())
            .unwrap_or_else(|| "api".to_string());
        let metadata = request.metadata.unwrap_or_default();

        let doc_id = request
            .document_id
            .unwrap_or_else(|| format!("doc-{}", &request_id.to_string()[..8]));

        let total_start = Instant::now();
        let parsed = ParsedDoc::from_text(request.markdown.clone());

        let coverage = coverage_features(&parsed.text, &parsed.lines, &parsed.tokens);
        let structure = structure_features(&parsed.text, &parsed.lines);
        let readability = readability_features(&parsed.tokens, parsed.sentence_count);
        let completeness = completeness_features(&coverage, &structure);
        let noise = noise_features(&parsed.text, &parsed.lines);
        let semantic_coherence_features =
            basic_semantic_coherence_features(&parsed.text, &parsed.tokens);

        let (semantic_info, semantic_ms) =
            self.semantic_engine.compute(&parsed.text, &parsed.tokens);

        let perplexity_start = Instant::now();
        let perplexity = self.perplexity_provider.score(&parsed.text).await?;
        let perplexity_ms = perplexity_start.elapsed().as_secs_f64() * 1000.0;

        let conversion_quality = evaluate_conversion(request.conversion.as_ref());

        let coverage_score_v = coverage_score(&coverage);
        let readability_score_v = readability_score(&readability);
        let completeness_score_v = completeness_score(&completeness);
        let structure_score_v = structure_score(&structure);
        let noise_score_v = noise_score(&noise);
        let info_density_score_v = info_density_score(&semantic_info);
        let semantic_coherence_score_v = semantic_coherence_score(&semantic_coherence_features);
        let value_score_v = value_score(
            coverage_score_v,
            completeness_score_v,
            info_density_score_v,
            readability_score_v,
        );
        let conversion_quality_score_v = conversion_quality
            .as_ref()
            .map(|v| v.conversion_quality_score)
            .unwrap_or(0.0);

        let dqi_total_v = dqi_total(
            coverage_score_v,
            readability_score_v,
            completeness_score_v,
            structure_score_v,
            noise_score_v,
            info_density_score_v,
            semantic_coherence_score_v,
            value_score_v,
            perplexity.score_0_100,
            conversion_quality_score_v,
            self.weights,
        );

        let mut features = BTreeMap::new();
        features.insert("coverage".to_string(), json!(coverage));
        features.insert("readability".to_string(), json!(readability));
        features.insert("completeness".to_string(), json!(completeness));
        features.insert("structure".to_string(), json!(structure));
        features.insert("noise".to_string(), json!(noise));
        features.insert("semantic".to_string(), json!(semantic_info));
        features.insert(
            "semantic_coherence".to_string(),
            json!(semantic_coherence_features),
        );
        features.insert(
            "perplexity".to_string(),
            json!({
                "provider": self.perplexity_provider.name(),
                "raw": perplexity.raw,
                "score_0_100": perplexity.score_0_100
            }),
        );

        let result = DocumentScoreResult {
            request_id,
            document_id: doc_id,
            source,
            markdown: request.markdown,
            created_at: Utc::now(),
            features,
            conversion_quality,
            scores: ScoreBreakdown {
                coverage_score: coverage_score_v,
                readability_score: readability_score_v,
                completeness_score: completeness_score_v,
                structure_score: structure_score_v,
                noise_score: noise_score_v,
                info_density_score: info_density_score_v,
                semantic_coherence_score: semantic_coherence_score_v,
                value_score: value_score_v,
                perplexity_score: perplexity.score_0_100,
                conversion_quality_score: conversion_quality_score_v,
                dqi_total: dqi_total_v,
            },
            timing: TimingInfo {
                processing_ms: total_start.elapsed().as_secs_f64() * 1000.0,
                semantic_inference_ms: semantic_ms,
                perplexity_ms,
            },
            metadata,
        };

        Ok(result)
    }

    pub async fn score_batch(
        &self,
        request: BatchScoreRequest,
    ) -> anyhow::Result<BatchScoreResponse> {
        let mut indexed_results = Vec::with_capacity(request.items.len());
        let mut items = request.items.into_iter().enumerate();
        let parallelism = self.batch_parallelism.max(1);

        loop {
            let mut join_set = JoinSet::new();
            for _ in 0..parallelism {
                if let Some((idx, item)) = items.next() {
                    let service = self.clone();
                    join_set.spawn(async move { (idx, service.score(item).await) });
                }
            }

            if join_set.is_empty() {
                break;
            }

            while let Some(joined) = join_set.join_next().await {
                let (idx, result) = joined.map_err(|e| anyhow::anyhow!(e.to_string()))?;
                indexed_results.push((idx, result?));
            }
        }

        indexed_results.sort_by_key(|(idx, _)| *idx);
        let results = indexed_results
            .into_iter()
            .map(|(_, result)| result)
            .collect::<Vec<_>>();

        Ok(BatchScoreResponse {
            count: results.len(),
            results,
        })
    }

    pub async fn readiness(&self) -> bool {
        true
    }

    pub fn warmup(&self) {
        self.semantic_engine.warmup();
    }
}
===


use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConversionProvider {
    Docling,
    Gemini,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversionInput {
    pub provider: ConversionProvider,
    pub source_page_count: Option<u32>,
    pub markdown_page_markers: Option<u32>,
    pub extraction_confidence: Option<f64>,
    pub dropped_blocks: Option<u32>,
    pub suspected_ocr_errors: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DocumentMetadata {
    pub source: Option<String>,
    pub language: Option<String>,
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreRequest {
    pub document_id: Option<String>,
    pub markdown: String,
    pub conversion: Option<ConversionInput>,
    pub metadata: Option<DocumentMetadata>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchScoreRequest {
    pub items: Vec<ScoreRequest>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchScoreResponse {
    pub count: usize,
    pub results: Vec<DocumentScoreResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversionQualityResult {
    pub completeness_confidence: f64,
    pub layout_consistency: f64,
    pub artifact_penalty: f64,
    pub conversion_quality_score: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreBreakdown {
    pub coverage_score: f64,
    pub readability_score: f64,
    pub completeness_score: f64,
    pub structure_score: f64,
    pub noise_score: f64,
    pub info_density_score: f64,
    pub semantic_coherence_score: f64,
    pub value_score: f64,
    pub perplexity_score: f64,
    pub conversion_quality_score: f64,
    pub dqi_total: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingInfo {
    pub processing_ms: f64,
    pub semantic_inference_ms: f64,
    pub perplexity_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentScoreResult {
    pub request_id: Uuid,
    pub document_id: String,
    pub source: String,
    pub markdown: String,
    pub created_at: DateTime<Utc>,
    pub features: BTreeMap<String, Value>,
    pub conversion_quality: Option<ConversionQualityResult>,
    pub scores: ScoreBreakdown,
    pub timing: TimingInfo,
    pub metadata: DocumentMetadata,
}

==
