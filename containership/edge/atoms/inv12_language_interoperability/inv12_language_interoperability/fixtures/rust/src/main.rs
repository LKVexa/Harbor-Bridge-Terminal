//! MC-020 Rust binding adapter and fixture component (std only, no crates).
//!
//! Descriptor-driven implementation of the INV-12 canonical ABI memory layout
//! plus the CJV/1 value notation, used as producer and consumer in the
//! cross-language conformance matrix (MC-024).
//!   inv12rs encode <vectors.json>
//!   inv12rs decode <vectors.json> <images.json>
use std::collections::HashSet;
use std::fs;

// ------------------------------------------------------------------ JSON
#[derive(Clone, Debug, PartialEq)]
enum J {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<J>),
    Obj(Vec<(String, J)>),
}

impl J {
    fn get(&self, k: &str) -> Option<&J> {
        match self {
            J::Obj(v) => v.iter().find(|(a, _)| a == k).map(|(_, b)| b),
            _ => None,
        }
    }
    fn s(&self) -> &str {
        match self {
            J::Str(s) => s,
            _ => "",
        }
    }
    fn arr(&self) -> &[J] {
        match self {
            J::Arr(v) => v,
            _ => &[],
        }
    }
}

struct P<'a> {
    b: &'a [u8],
    i: usize,
}

impl<'a> P<'a> {
    fn ws(&mut self) {
        while self.i < self.b.len() && (self.b[self.i] as char).is_ascii_whitespace() {
            self.i += 1;
        }
    }
    fn val(&mut self) -> J {
        self.ws();
        match self.b[self.i] {
            b'{' => {
                self.i += 1;
                let mut v = Vec::new();
                loop {
                    self.ws();
                    if self.b[self.i] == b'}' {
                        self.i += 1;
                        break;
                    }
                    let k = match self.val() {
                        J::Str(s) => s,
                        _ => panic!("key"),
                    };
                    self.ws();
                    self.i += 1; // ':'
                    let x = self.val();
                    v.push((k, x));
                    self.ws();
                    if self.b[self.i] == b',' {
                        self.i += 1;
                    }
                }
                J::Obj(v)
            }
            b'[' => {
                self.i += 1;
                let mut v = Vec::new();
                loop {
                    self.ws();
                    if self.b[self.i] == b']' {
                        self.i += 1;
                        break;
                    }
                    v.push(self.val());
                    self.ws();
                    if self.b[self.i] == b',' {
                        self.i += 1;
                    }
                }
                J::Arr(v)
            }
            b'"' => {
                self.i += 1;
                let mut s = String::new();
                loop {
                    let c = self.b[self.i];
                    self.i += 1;
                    match c {
                        b'"' => break,
                        b'\\' => {
                            let e = self.b[self.i];
                            self.i += 1;
                            match e {
                                b'n' => s.push('\n'),
                                b't' => s.push('\t'),
                                b'r' => s.push('\r'),
                                b'b' => s.push('\u{8}'),
                                b'f' => s.push('\u{c}'),
                                b'u' => {
                                    let mut cp = self.hex4();
                                    if (0xD800..0xDC00).contains(&cp) {
                                        self.i += 2; // \u
                                        let lo = self.hex4();
                                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                                    }
                                    s.push(char::from_u32(cp).expect("scalar"));
                                }
                                x => s.push(x as char),
                            }
                        }
                        _ => {
                            // raw UTF-8 byte run
                            let start = self.i - 1;
                            let mut end = self.i;
                            while end < self.b.len() && self.b[end] != b'"' && self.b[end] != b'\\' {
                                end += 1;
                            }
                            s.push_str(std::str::from_utf8(&self.b[start..end]).expect("utf8"));
                            self.i = end;
                        }
                    }
                }
                J::Str(s)
            }
            b't' => {
                self.i += 4;
                J::Bool(true)
            }
            b'f' => {
                self.i += 5;
                J::Bool(false)
            }
            b'n' => {
                self.i += 4;
                J::Null
            }
            _ => {
                let st = self.i;
                while self.i < self.b.len() && b"+-0123456789.eE".contains(&self.b[self.i]) {
                    self.i += 1;
                }
                J::Num(std::str::from_utf8(&self.b[st..self.i]).unwrap().parse().unwrap())
            }
        }
    }
    fn hex4(&mut self) -> u32 {
        let h = std::str::from_utf8(&self.b[self.i..self.i + 4]).unwrap();
        self.i += 4;
        u32::from_str_radix(h, 16).unwrap()
    }
}

fn dump(j: &J, o: &mut String) {
    match j {
        J::Null => o.push_str("null"),
        J::Bool(b) => o.push_str(if *b { "true" } else { "false" }),
        J::Num(n) => o.push_str(&format!("{}", n)),
        J::Str(s) => {
            o.push('"');
            for c in s.chars() {
                match c {
                    '"' => o.push_str("\\\""),
                    '\\' => o.push_str("\\\\"),
                    c if (c as u32) < 0x20 => o.push_str(&format!("\\u{:04x}", c as u32)),
                    c => o.push(c),
                }
            }
            o.push('"');
        }
        J::Arr(v) => {
            o.push('[');
            for (i, x) in v.iter().enumerate() {
                if i > 0 {
                    o.push(',');
                }
                dump(x, o);
            }
            o.push(']');
        }
        J::Obj(v) => {
            o.push('{');
            for (i, (k, x)) in v.iter().enumerate() {
                if i > 0 {
                    o.push(',');
                }
                dump(&J::Str(k.clone()), o);
                o.push(':');
                dump(x, o);
            }
            o.push('}');
        }
    }
}

// ------------------------------------------------------------------ ABI
type R<T> = Result<T, &'static str>;
const U32MAX: u64 = u32::MAX as u64;

fn prim(k: &str) -> Option<(u64, u64)> {
    Some(match k {
        "bool" | "s8" | "u8" => (1, 1),
        "s16" | "u16" => (2, 2),
        "s32" | "u32" | "f32" | "char" => (4, 4),
        "s64" | "u64" | "f64" => (8, 8),
        "string" => (8, 4),
        _ => return None,
    })
}
fn kind(t: &J) -> &str {
    t.get("k").map(|x| x.s()).unwrap_or("")
}
fn disc_size(n: usize) -> u64 {
    if n <= 256 { 1 } else if n <= 65536 { 2 } else { 4 }
}
fn flags_size(n: usize) -> u64 {
    if n == 0 { 0 } else if n <= 8 { 1 } else if n <= 16 { 2 } else { 4 * (n as u64).div_ceil(32) }
}
fn align_up(p: u64, a: u64) -> R<u64> {
    let r = p.div_ceil(a) * a;
    if r > U32MAX { Err("PK_INTEROP_MEMORY_OVERFLOW") } else { Ok(r) }
}
fn cases(t: &J) -> (Vec<String>, Vec<Option<J>>) {
    let opt = |x: Option<&J>| match x {
        None | Some(J::Null) => None,
        Some(j) => Some(j.clone()),
    };
    match kind(t) {
        "variant" => t.get("cases").unwrap().arr().iter()
            .map(|c| (c.arr()[0].s().to_string(), opt(c.arr().get(1)))).unzip(),
        "enum" => t.get("cases").unwrap().arr().iter().map(|c| (c.s().to_string(), None)).unzip(),
        "option" => (vec!["none".into(), "some".into()], vec![None, opt(t.get("t"))]),
        "result" => (vec!["ok".into(), "error".into()], vec![opt(t.get("ok")), opt(t.get("err"))]),
        _ => (vec![], vec![]),
    }
}
fn fields(t: &J) -> (Vec<String>, Vec<J>) {
    if kind(t) == "tuple" {
        return t.get("ts").unwrap().arr().iter().enumerate()
            .map(|(i, x)| (i.to_string(), x.clone())).unzip();
    }
    t.get("fields").unwrap().arr().iter()
        .map(|f| (f.arr()[0].s().to_string(), f.arr()[1].clone())).unzip()
}
fn align(t: &J) -> u64 {
    let k = kind(t);
    if let Some(p) = prim(k) {
        return p.1;
    }
    match k {
        "list" | "own" | "borrow" | "future" | "stream" => 4,
        "record" | "tuple" => fields(t).1.iter().map(align).max().unwrap_or(1).max(1),
        "flags" => {
            let n = t.get("names").unwrap().arr().len();
            if n <= 8 { 1 } else if n <= 16 { 2 } else { 4 }
        }
        _ => {
            let (ns, ps) = cases(t);
            ps.iter().flatten().map(align).fold(disc_size(ns.len()), u64::max)
        }
    }
}
fn max_case_align(ps: &[Option<J>]) -> u64 {
    ps.iter().flatten().map(align).fold(1, u64::max)
}
fn size(t: &J) -> R<u64> {
    let k = kind(t);
    if let Some(p) = prim(k) {
        return Ok(p.0);
    }
    Ok(match k {
        "list" => 8,
        "own" | "borrow" | "future" | "stream" => 4,
        "record" | "tuple" => {
            let mut s = 0;
            for f in fields(t).1 {
                s = align_up(s, align(&f))? + size(&f)?;
            }
            align_up(s, align(t))?
        }
        "flags" => flags_size(t.get("names").unwrap().arr().len()),
        _ => {
            let (ns, ps) = cases(t);
            let s = align_up(disc_size(ns.len()), max_case_align(&ps))?;
            let mut m = 0;
            for p in ps.iter().flatten() {
                m = m.max(size(p)?);
            }
            align_up(s + m, align(t))?
        }
    })
}

struct Mem {
    b: Vec<u8>,
    pos: u64,
}

impl Mem {
    fn alloc(&mut self, a: u64, n: u64) -> R<u64> {
        let p = align_up(self.pos, a)?;
        if p + n > U32MAX {
            return Err("PK_INTEROP_MEMORY_OVERFLOW");
        }
        self.pos = p + n;
        if (self.b.len() as u64) < self.pos {
            self.b.resize(self.pos as usize, 0);
        }
        Ok(p)
    }
    fn check(&self, p: u64, n: u64, a: u64) -> R<()> {
        if p > U32MAX || n > U32MAX || p + n > U32MAX {
            return Err("PK_INTEROP_MEMORY_OVERFLOW");
        }
        if p + n > self.b.len() as u64 {
            return Err("PK_INTEROP_MEMORY_BOUNDS");
        }
        if a > 1 && !p.is_multiple_of(a) {
            return Err("PK_INTEROP_MEMORY_ALIGNMENT");
        }
        Ok(())
    }
    fn ld(&self, p: u64, n: u64) -> R<u64> {
        self.check(p, n, n)?;
        let mut v = 0u64;
        for i in (0..n).rev() {
            v = (v << 8) | self.b[(p + i) as usize] as u64;
        }
        Ok(v)
    }
    fn st(&mut self, p: u64, n: u64, mut v: u64) -> R<()> {
        self.check(p, n, n)?;
        for i in 0..n {
            self.b[(p + i) as usize] = (v & 0xff) as u8;
            v >>= 8;
        }
        Ok(())
    }
}

fn parse_int(k: &str, s: &str) -> R<u64> {
    let w = prim(k).unwrap().0 * 8;
    let v: i128 = s.parse().map_err(|_| "PK_INTEROP_TYPE_MISMATCH")?;
    let (lo, hi): (i128, i128) = if k.starts_with('s') {
        (-(1i128 << (w - 1)), (1i128 << (w - 1)) - 1)
    } else {
        (0, (1i128 << w) - 1)
    };
    if v < lo || v > hi {
        return Err("PK_INTEROP_OUT_OF_RANGE");
    }
    Ok((v as u128 & ((1u128 << w) - 1)) as u64)
}

fn store(m: &mut Mem, v: &J, t: &J, p: u64) -> R<()> {
    let k = kind(t);
    match k {
        "bool" => return m.st(p, 1, matches!(v, J::Bool(true)) as u64),
        "s8" | "u8" | "s16" | "u16" | "s32" | "u32" | "s64" | "u64" => {
            return m.st(p, prim(k).unwrap().0, parse_int(k, v.s())?)
        }
        "f32" | "f64" => {
            let b = u64::from_str_radix(&v.s()[2..], 16).map_err(|_| "PK_INTEROP_TYPE_MISMATCH")?;
            return m.st(p, prim(k).unwrap().0, b);
        }
        "char" => {
            let c: u64 = v.s().parse().map_err(|_| "PK_INTEROP_TYPE_MISMATCH")?;
            if (0xD800..=0xDFFF).contains(&c) || c > 0x10FFFF {
                return Err("PK_INTEROP_ENCODING");
            }
            return m.st(p, 4, c);
        }
        "string" => {
            let s = v.s().as_bytes(); // Rust String is always valid UTF-8
            let q = m.alloc(1, s.len() as u64)?;
            m.b[q as usize..q as usize + s.len()].copy_from_slice(s);
            m.st(p, 4, q)?;
            return m.st(p + 4, 4, s.len() as u64);
        }
        "list" => {
            let el = t.get("t").unwrap();
            let xs = v.arr();
            let es = size(el)?;
            let q = m.alloc(align(el), xs.len() as u64 * es)?;
            for (i, x) in xs.iter().enumerate() {
                store(m, x, el, q + i as u64 * es)?;
            }
            m.st(p, 4, q)?;
            return m.st(p + 4, 4, xs.len() as u64);
        }
        "record" | "tuple" => {
            let (ns, ts) = fields(t);
            let mut off = 0;
            for (i, n) in ns.iter().enumerate() {
                off = align_up(off, align(&ts[i]))?;
                let fv = if k == "tuple" { &v.arr()[i] } else { v.get(n).ok_or("PK_INTEROP_TYPE_MISMATCH")? };
                store(m, fv, &ts[i], p + off)?;
                off += size(&ts[i])?;
            }
            return Ok(());
        }
        "flags" => {
            let names = t.get("names").unwrap().arr();
            let set: HashSet<&str> = v.arr().iter().map(|x| x.s()).collect();
            let mut words = vec![0u64; names.len() / 32 + 1];
            for (i, n) in names.iter().enumerate() {
                if set.contains(n.s()) {
                    words[i / 32] |= 1 << (i % 32);
                }
            }
            let sz = flags_size(names.len());
            if sz == 1 || sz == 2 {
                return m.st(p, sz, words[0]);
            }
            for w in 0..(sz / 4) {
                m.st(p + 4 * w, 4, words[w as usize])?;
            }
            return Ok(());
        }
        "own" | "borrow" | "future" | "stream" => {
            let h: u64 = v.s().parse().map_err(|_| "PK_INTEROP_HANDLE")?;
            if h == 0 || h > U32MAX {
                return Err("PK_INTEROP_HANDLE");
            }
            return m.st(p, 4, h);
        }
        _ => {}
    }
    let (ns, ps) = cases(t);
    let (cname, payload): (String, Option<&J>) = match k {
        "enum" => (v.s().to_string(), None),
        "option" => match v {
            J::Null => ("none".into(), None),
            _ => ("some".into(), v.get("some")),
        },
        "result" => match v.get("ok") {
            Some(x) => ("ok".into(), Some(x)),
            None => ("error".into(), v.get("error")),
        },
        _ => (v.get("case").map(|x| x.s().to_string()).unwrap_or_default(), v.get("value")),
    };
    let idx = ns.iter().position(|n| *n == cname).ok_or("PK_INTEROP_INVALID_DISCRIMINANT")?;
    m.st(p, disc_size(ns.len()), idx as u64)?;
    if let Some(pt) = &ps[idx] {
        let off = align_up(disc_size(ns.len()), max_case_align(&ps))?;
        store(m, payload.ok_or("PK_INTEROP_TYPE_MISMATCH")?, pt, p + off)?;
    }
    Ok(())
}

fn load(m: &Mem, p: u64, t: &J) -> R<J> {
    let k = kind(t);
    Ok(match k {
        "bool" => J::Bool(m.ld(p, 1)? != 0),
        "u8" | "u16" | "u32" | "u64" => J::Str(m.ld(p, prim(k).unwrap().0)?.to_string()),
        "s8" | "s16" | "s32" | "s64" => {
            let w = prim(k).unwrap().0;
            let u = m.ld(p, w)?;
            let sh = 64 - 8 * w;
            J::Str((((u << sh) as i64) >> sh).to_string())
        }
        "f32" => {
            let mut b = m.ld(p, 4)?;
            if f32::from_bits(b as u32).is_nan() {
                b = 0x7fc00000;
            }
            J::Str(format!("0x{:08x}", b))
        }
        "f64" => {
            let mut b = m.ld(p, 8)?;
            if f64::from_bits(b).is_nan() {
                b = 0x7ff8000000000000;
            }
            J::Str(format!("0x{:016x}", b))
        }
        "char" => {
            let c = m.ld(p, 4)?;
            if char::from_u32(c as u32).is_none() {
                return Err("PK_INTEROP_ENCODING");
            }
            J::Str(c.to_string())
        }
        "string" => {
            let (q, n) = (m.ld(p, 4)?, m.ld(p + 4, 4)?);
            m.check(q, n, 1)?;
            let s = std::str::from_utf8(&m.b[q as usize..(q + n) as usize]).map_err(|_| "PK_INTEROP_ENCODING")?;
            J::Str(s.to_string())
        }
        "list" => {
            let el = t.get("t").unwrap();
            let (q, n) = (m.ld(p, 4)?, m.ld(p + 4, 4)?);
            let es = size(el)?;
            let total = n.checked_mul(es).filter(|x| *x <= U32MAX).ok_or("PK_INTEROP_MEMORY_OVERFLOW")?;
            m.check(q, total, align(el))?;
            if es == 0 && n > 1_000_000 {
                return Err("PK_INTEROP_LIMIT");
            }
            let mut out = Vec::new();
            for i in 0..n {
                out.push(load(m, q + i * es, el)?);
            }
            J::Arr(out)
        }
        "record" | "tuple" => {
            let (ns, ts) = fields(t);
            let mut off = 0;
            let mut obj = Vec::new();
            for (i, n) in ns.iter().enumerate() {
                off = align_up(off, align(&ts[i]))?;
                obj.push((n.clone(), load(m, p + off, &ts[i])?));
                off += size(&ts[i])?;
            }
            if k == "tuple" { J::Arr(obj.into_iter().map(|x| x.1).collect()) } else { J::Obj(obj) }
        }
        "flags" => {
            let names = t.get("names").unwrap().arr();
            let sz = flags_size(names.len());
            if sz == 0 {
                return Ok(J::Arr(vec![]));
            }
            let words: Vec<u64> = if sz <= 2 {
                vec![m.ld(p, sz)?]
            } else {
                (0..sz / 4).map(|w| m.ld(p + 4 * w, 4)).collect::<R<_>>()?
            };
            for (w, word) in words.iter().enumerate() {
                for b in 0..32 {
                    if word >> b & 1 == 1 && w * 32 + b >= names.len() {
                        return Err("PK_INTEROP_INVALID_FLAGS");
                    }
                }
            }
            J::Arr(names.iter().enumerate().filter(|(i, _)| words[i / 32] >> (i % 32) & 1 == 1)
                .map(|(_, n)| n.clone()).collect())
        }
        "own" | "borrow" | "future" | "stream" => {
            let h = m.ld(p, 4)?;
            if h == 0 {
                return Err("PK_INTEROP_HANDLE");
            }
            J::Str(h.to_string())
        }
        _ => {
            let (ns, ps) = cases(t);
            let idx = m.ld(p, disc_size(ns.len()))? as usize;
            if idx >= ns.len() {
                return Err("PK_INTEROP_INVALID_DISCRIMINANT");
            }
            let payload = match &ps[idx] {
                Some(pt) => Some(load(m, p + align_up(disc_size(ns.len()), max_case_align(&ps))?, pt)?),
                None => None,
            };
            let c = ns[idx].clone();
            match k {
                "enum" => J::Str(c),
                "option" => match payload {
                    None if c == "none" => J::Null,
                    x => J::Obj(vec![("some".into(), x.unwrap_or(J::Null))]),
                },
                "result" => J::Obj(vec![(c, payload.unwrap_or(J::Null))]),
                _ => match payload {
                    None => J::Obj(vec![("case".into(), J::Str(c))]),
                    Some(x) => J::Obj(vec![("case".into(), J::Str(c)), ("value".into(), x)]),
                },
            }
        }
    })
}

fn hexs(b: &[u8]) -> String {
    b.iter().map(|x| format!("{:02x}", x)).collect()
}
fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}
fn read(path: &str) -> J {
    let raw = fs::read(path).expect("read");
    P { b: &raw, i: 0 }.val()
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let vec = read(&a[2]);
    let mut out = Vec::new();
    match a[1].as_str() {
        "encode" => {
            for v in vec.get("valid").unwrap().arr() {
                let t = v.get("descriptor").unwrap();
                let mut m = Mem { b: vec![], pos: 0 };
                let r = (|| -> R<u64> {
                    let root = m.alloc(align(t), size(t)?)?;
                    store(&mut m, v.get("value").unwrap(), t, root)?;
                    Ok(root)
                })();
                let rec = match r {
                    Ok(root) => J::Obj(vec![("image".into(), J::Str(hexs(&m.b))), ("root".into(), J::Num(root as f64))]),
                    Err(e) => J::Obj(vec![("err".into(), J::Str(e.into()))]),
                };
                out.push((v.get("id").unwrap().s().to_string(), rec));
            }
        }
        "decode" => {
            let imgs = read(&a[3]);
            let all: Vec<&J> = vec.get("valid").unwrap().arr().iter()
                .chain(vec.get("invalid").unwrap().arr().iter()).collect();
            for v in all {
                let id = v.get("id").unwrap().s().to_string();
                let src = match imgs.get(&id) {
                    Some(s) => s,
                    None => continue,
                };
                if src.get("err").is_some() {
                    out.push((id, J::Obj(vec![("err".into(), J::Str("PRODUCER_FAILED".into()))])));
                    continue;
                }
                let root = match src.get("root") {
                    Some(J::Num(n)) => *n as u64,
                    _ => 0,
                };
                let m = Mem { b: unhex(src.get("image").unwrap().s()), pos: 0 };
                let rec = match load(&m, root, v.get("descriptor").unwrap()) {
                    Ok(x) => J::Obj(vec![("ok".into(), x)]),
                    Err(e) => J::Obj(vec![("err".into(), J::Str(e.into()))]),
                };
                out.push((id, rec));
            }
        }
        "bench" => {
            // MC-034: per-operation lower+lift latency on selected golden vectors.
            for v in vec.get("valid").unwrap().arr() {
                let id = v.get("id").unwrap().s();
                if !["u32-max", "record-point", "record-doc", "list-string"].contains(&id) {
                    continue;
                }
                let t = v.get("descriptor").unwrap();
                let val = v.get("value").unwrap();
                let n = if id == "record-doc" { 50_000 } else { 200_000 };
                let mut lat = Vec::with_capacity(n);
                for _ in 0..n {
                    let t0 = std::time::Instant::now();
                    let mut m = Mem { b: vec![], pos: 0 };
                    let root = m.alloc(align(t), size(t).unwrap()).unwrap();
                    store(&mut m, val, t, root).unwrap();
                    std::hint::black_box(load(&m, root, t).unwrap());
                    lat.push(t0.elapsed().as_nanos() as f64);
                }
                lat.sort_by(|a, b| a.partial_cmp(b).unwrap());
                out.push((id.to_string(), J::Obj(vec![
                    ("n".into(), J::Num(n as f64)),
                    ("p50_ns".into(), J::Num(lat[n / 2])),
                    ("p95_ns".into(), J::Num(lat[n * 95 / 100])),
                    ("p99_ns".into(), J::Num(lat[n * 99 / 100])),
                ])));
            }
        }
        _ => std::process::exit(2),
    }
    let mut s = String::new();
    dump(&J::Obj(out), &mut s);
    println!("{}", s);
}
