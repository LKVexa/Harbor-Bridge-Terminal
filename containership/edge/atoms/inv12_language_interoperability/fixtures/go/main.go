// MC-021 Go binding adapter and fixture component (stdlib only).
//
// Implements the INV-12 canonical ABI memory layout from type descriptors and
// the CJV/1 value notation, so that Go can act as producer (encode) and
// consumer (decode) in the cross-language conformance matrix (MC-024).
//
//   go run . encode <vectors.json>            -> {"id": "<hex image>", ...}
//   go run . decode <vectors.json> <images>   -> {"id": {"ok": cjv} | {"err": code}}
//   go run . selftest <vectors.json>          -> summary (golden corpus)
package main

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"sort"
	"strconv"
	"time"
	"unicode/utf8"
)

type D = map[string]interface{}

type abiErr struct{ code string }

func (e abiErr) Error() string { return e.code }

func fail(code string) { panic(abiErr{code}) }

const u32max = uint64(math.MaxUint32)

var prim = map[string][2]int{"bool": {1, 1}, "s8": {1, 1}, "u8": {1, 1}, "s16": {2, 2}, "u16": {2, 2},
	"s32": {4, 4}, "u32": {4, 4}, "s64": {8, 8}, "u64": {8, 8}, "f32": {4, 4}, "f64": {8, 8},
	"char": {4, 4}, "string": {8, 4}}

func kind(t D) string { return t["k"].(string) }

func discSize(n int) int {
	if n <= 256 {
		return 1
	} else if n <= 65536 {
		return 2
	}
	return 4
}

func alignUp(p, a uint64) uint64 {
	r := (p + a - 1) &^ (a - 1)
	if r > u32max {
		fail("PK_INTEROP_MEMORY_OVERFLOW")
	}
	return r
}

// cases returns (name, payload-descriptor-or-nil) for the variant family.
func cases(t D) ([]string, []D) {
	switch kind(t) {
	case "variant":
		var ns []string
		var ps []D
		for _, c := range t["cases"].([]interface{}) {
			cc := c.([]interface{})
			ns = append(ns, cc[0].(string))
			if cc[1] == nil {
				ps = append(ps, nil)
			} else {
				ps = append(ps, cc[1].(D))
			}
		}
		return ns, ps
	case "enum":
		var ns []string
		var ps []D
		for _, c := range t["cases"].([]interface{}) {
			ns = append(ns, c.(string))
			ps = append(ps, nil)
		}
		return ns, ps
	case "option":
		return []string{"none", "some"}, []D{nil, t["t"].(D)}
	case "result":
		var ok, er D
		if t["ok"] != nil {
			ok = t["ok"].(D)
		}
		if t["err"] != nil {
			er = t["err"].(D)
		}
		return []string{"ok", "error"}, []D{ok, er}
	}
	return nil, nil
}

func fields(t D) ([]string, []D) {
	var ns []string
	var ts []D
	if kind(t) == "tuple" {
		for i, x := range t["ts"].([]interface{}) {
			ns = append(ns, strconv.Itoa(i))
			ts = append(ts, x.(D))
		}
		return ns, ts
	}
	for _, f := range t["fields"].([]interface{}) {
		ff := f.([]interface{})
		ns = append(ns, ff[0].(string))
		ts = append(ts, ff[1].(D))
	}
	return ns, ts
}

func flagsSize(n int) int {
	switch {
	case n == 0:
		return 0
	case n <= 8:
		return 1
	case n <= 16:
		return 2
	}
	return 4 * ((n + 31) / 32)
}

func align(t D) uint64 {
	k := kind(t)
	if p, ok := prim[k]; ok {
		return uint64(p[1])
	}
	switch k {
	case "list", "own", "borrow", "future", "stream":
		return 4
	case "record", "tuple":
		_, ts := fields(t)
		m := uint64(1)
		for _, x := range ts {
			if a := align(x); a > m {
				m = a
			}
		}
		return m
	case "flags":
		n := len(t["names"].([]interface{}))
		if n <= 8 {
			return 1
		} else if n <= 16 {
			return 2
		}
		return 4
	}
	ns, ps := cases(t)
	m := uint64(discSize(len(ns)))
	for _, p := range ps {
		if p != nil {
			if a := align(p); a > m {
				m = a
			}
		}
	}
	return m
}

func maxCaseAlign(ps []D) uint64 {
	m := uint64(1)
	for _, p := range ps {
		if p != nil {
			if a := align(p); a > m {
				m = a
			}
		}
	}
	return m
}

func size(t D) uint64 {
	k := kind(t)
	if p, ok := prim[k]; ok {
		return uint64(p[0])
	}
	switch k {
	case "list":
		return 8
	case "own", "borrow", "future", "stream":
		return 4
	case "record", "tuple":
		_, ts := fields(t)
		s := uint64(0)
		for _, x := range ts {
			s = alignUp(s, align(x)) + size(x)
		}
		return alignUp(s, align(t))
	case "flags":
		return uint64(flagsSize(len(t["names"].([]interface{}))))
	}
	ns, ps := cases(t)
	s := alignUp(uint64(discSize(len(ns))), maxCaseAlign(ps))
	m := uint64(0)
	for _, p := range ps {
		if p != nil {
			if z := size(p); z > m {
				m = z
			}
		}
	}
	return alignUp(s+m, align(t))
}

// ------------------------------------------------------------------ memory
type Mem struct {
	b   []byte
	pos uint64
}

func (m *Mem) alloc(a, n uint64) uint64 {
	p := alignUp(m.pos, a)
	if p+n > u32max {
		fail("PK_INTEROP_MEMORY_OVERFLOW")
	}
	m.pos = p + n
	for uint64(len(m.b)) < m.pos {
		m.b = append(m.b, 0)
	}
	return p
}

func (m *Mem) check(p, n, a uint64) {
	if p > u32max || n > u32max || p+n > u32max {
		fail("PK_INTEROP_MEMORY_OVERFLOW")
	}
	if p+n > uint64(len(m.b)) {
		fail("PK_INTEROP_MEMORY_BOUNDS")
	}
	if a > 1 && p%a != 0 {
		fail("PK_INTEROP_MEMORY_ALIGNMENT")
	}
}

func (m *Mem) ld(p uint64, n int) uint64 {
	m.check(p, uint64(n), uint64(n))
	switch n {
	case 1:
		return uint64(m.b[p])
	case 2:
		return uint64(binary.LittleEndian.Uint16(m.b[p:]))
	case 4:
		return uint64(binary.LittleEndian.Uint32(m.b[p:]))
	}
	return binary.LittleEndian.Uint64(m.b[p:])
}

func (m *Mem) st(p uint64, n int, v uint64) {
	m.check(p, uint64(n), uint64(n))
	switch n {
	case 1:
		m.b[p] = byte(v)
	case 2:
		binary.LittleEndian.PutUint16(m.b[p:], uint16(v))
	case 4:
		binary.LittleEndian.PutUint32(m.b[p:], uint32(v))
	default:
		binary.LittleEndian.PutUint64(m.b[p:], v)
	}
}

func parseInt(k string, s string) uint64 {
	w := prim[k][0] * 8
	if k[0] == 's' {
		v, err := strconv.ParseInt(s, 10, w)
		if err != nil {
			fail("PK_INTEROP_OUT_OF_RANGE")
		}
		return uint64(v) & (math.MaxUint64 >> (64 - w))
	}
	v, err := strconv.ParseUint(s, 10, w)
	if err != nil {
		fail("PK_INTEROP_OUT_OF_RANGE")
	}
	return v
}

func store(m *Mem, v interface{}, t D, p uint64) {
	k := kind(t)
	switch k {
	case "bool":
		if v.(bool) {
			m.st(p, 1, 1)
		} else {
			m.st(p, 1, 0)
		}
		return
	case "s8", "u8", "s16", "u16", "s32", "u32", "s64", "u64":
		m.st(p, prim[k][0], parseInt(k, v.(string)))
		return
	case "f32", "f64":
		b, err := strconv.ParseUint(v.(string)[2:], 16, 64)
		if err != nil {
			fail("PK_INTEROP_TYPE_MISMATCH")
		}
		m.st(p, prim[k][0], b)
		return
	case "char":
		c, _ := strconv.ParseUint(v.(string), 10, 32)
		if (c >= 0xD800 && c <= 0xDFFF) || c > 0x10FFFF {
			fail("PK_INTEROP_ENCODING")
		}
		m.st(p, 4, c)
		return
	case "string":
		s := v.(string)
		if !utf8.ValidString(s) {
			fail("PK_INTEROP_ENCODING")
		}
		q := m.alloc(1, uint64(len(s)))
		copy(m.b[q:], s)
		m.st(p, 4, q)
		m.st(p+4, 4, uint64(len(s)))
		return
	case "list":
		el := t["t"].(D)
		xs := v.([]interface{})
		es := size(el)
		q := m.alloc(align(el), uint64(len(xs))*es)
		for i, x := range xs {
			store(m, x, el, q+uint64(i)*es)
		}
		m.st(p, 4, q)
		m.st(p+4, 4, uint64(len(xs)))
		return
	case "record", "tuple":
		ns, ts := fields(t)
		off := uint64(0)
		for i, n := range ns {
			off = alignUp(off, align(ts[i]))
			var fv interface{}
			if k == "tuple" {
				fv = v.([]interface{})[i]
			} else {
				fv = v.(D)[n]
			}
			store(m, fv, ts[i], p+off)
			off += size(ts[i])
		}
		return
	case "flags":
		names := t["names"].([]interface{})
		set := map[string]bool{}
		for _, x := range v.([]interface{}) {
			set[x.(string)] = true
		}
		sz := flagsSize(len(names))
		words := make([]uint64, (len(names)+31)/32+1)
		for i, n := range names {
			if set[n.(string)] {
				words[i/32] |= 1 << (uint(i) % 32)
			}
		}
		if sz == 1 || sz == 2 {
			m.st(p, sz, words[0])
		} else {
			for w := 0; w < sz/4; w++ {
				m.st(p+uint64(4*w), 4, words[w])
			}
		}
		return
	case "own", "borrow", "future", "stream":
		h, err := strconv.ParseUint(v.(string), 10, 32)
		if err != nil || h == 0 {
			fail("PK_INTEROP_HANDLE")
		}
		m.st(p, 4, h)
		return
	}
	ns, ps := cases(t)
	var cname string
	var payload interface{}
	switch k {
	case "enum":
		cname = v.(string)
	case "option":
		if v == nil {
			cname = "none"
		} else {
			cname, payload = "some", v.(D)["some"]
		}
	case "result":
		mv := v.(D)
		if x, ok := mv["ok"]; ok {
			cname, payload = "ok", x
		} else {
			cname, payload = "error", mv["error"]
		}
	default:
		mv := v.(D)
		cname, payload = mv["case"].(string), mv["value"]
	}
	idx := -1
	for i, n := range ns {
		if n == cname {
			idx = i
		}
	}
	if idx < 0 {
		fail("PK_INTEROP_INVALID_DISCRIMINANT")
	}
	m.st(p, discSize(len(ns)), uint64(idx))
	if ps[idx] != nil {
		store(m, payload, ps[idx], p+alignUp(uint64(discSize(len(ns))), maxCaseAlign(ps)))
	}
}

func load(m *Mem, p uint64, t D) interface{} {
	k := kind(t)
	switch k {
	case "bool":
		return m.ld(p, 1) != 0
	case "u8", "u16", "u32", "u64":
		return strconv.FormatUint(m.ld(p, prim[k][0]), 10)
	case "s8", "s16", "s32", "s64":
		w := prim[k][0]
		u := m.ld(p, w)
		sh := uint(64 - 8*w)
		return strconv.FormatInt(int64(u<<sh)>>sh, 10)
	case "f32":
		b := m.ld(p, 4)
		if math.IsNaN(float64(math.Float32frombits(uint32(b)))) {
			b = 0x7fc00000
		}
		return fmt.Sprintf("0x%08x", b)
	case "f64":
		b := m.ld(p, 8)
		if math.IsNaN(math.Float64frombits(b)) {
			b = 0x7ff8000000000000
		}
		return fmt.Sprintf("0x%016x", b)
	case "char":
		c := m.ld(p, 4)
		if (c >= 0xD800 && c <= 0xDFFF) || c > 0x10FFFF {
			fail("PK_INTEROP_ENCODING")
		}
		return strconv.FormatUint(c, 10)
	case "string":
		q, n := m.ld(p, 4), m.ld(p+4, 4)
		m.check(q, n, 1)
		b := m.b[q : q+n]
		if !utf8.Valid(b) {
			fail("PK_INTEROP_ENCODING")
		}
		return string(b)
	case "list":
		el := t["t"].(D)
		q, n := m.ld(p, 4), m.ld(p+4, 4)
		es := size(el)
		if n*es > u32max {
			fail("PK_INTEROP_MEMORY_OVERFLOW")
		}
		m.check(q, n*es, align(el))
		if es == 0 && n > 1000000 {
			fail("PK_INTEROP_LIMIT")
		}
		out := make([]interface{}, 0, n)
		for i := uint64(0); i < n; i++ {
			out = append(out, load(m, q+i*es, el))
		}
		return out
	case "record", "tuple":
		ns, ts := fields(t)
		off := uint64(0)
		rec := D{}
		arr := []interface{}{}
		for i, n := range ns {
			off = alignUp(off, align(ts[i]))
			x := load(m, p+off, ts[i])
			rec[n] = x
			arr = append(arr, x)
			off += size(ts[i])
		}
		if k == "tuple" {
			return arr
		}
		return rec
	case "flags":
		names := t["names"].([]interface{})
		sz := flagsSize(len(names))
		out := []interface{}{}
		if sz == 0 {
			return out
		}
		var words []uint64
		if sz == 1 || sz == 2 {
			words = []uint64{m.ld(p, sz)}
		} else {
			for w := 0; w < sz/4; w++ {
				words = append(words, m.ld(p+uint64(4*w), 4))
			}
		}
		for w, word := range words {
			for b := 0; b < 32; b++ {
				if word>>uint(b)&1 == 1 {
					i := w*32 + b
					if i >= len(names) {
						fail("PK_INTEROP_INVALID_FLAGS")
					}
				}
			}
		}
		for i, n := range names {
			if words[i/32]>>(uint(i)%32)&1 == 1 {
				out = append(out, n)
			}
		}
		return out
	case "own", "borrow", "future", "stream":
		h := m.ld(p, 4)
		if h == 0 {
			fail("PK_INTEROP_HANDLE")
		}
		return strconv.FormatUint(h, 10)
	}
	ns, ps := cases(t)
	idx := m.ld(p, discSize(len(ns)))
	if idx >= uint64(len(ns)) {
		fail("PK_INTEROP_INVALID_DISCRIMINANT")
	}
	var payload interface{}
	if ps[idx] != nil {
		payload = load(m, p+alignUp(uint64(discSize(len(ns))), maxCaseAlign(ps)), ps[idx])
	}
	c := ns[idx]
	switch k {
	case "enum":
		return c
	case "option":
		if c == "none" {
			return nil
		}
		return D{"some": payload}
	case "result":
		return D{c: payload}
	}
	if ps[idx] == nil {
		return D{"case": c}
	}
	return D{"case": c, "value": payload}
}

func encode(v interface{}, t D) (img string, err string) {
	defer func() {
		if r := recover(); r != nil {
			if e, ok := r.(abiErr); ok {
				err = e.code
				return
			}
			err = fmt.Sprint("PANIC:", r)
		}
	}()
	m := &Mem{}
	root := m.alloc(align(t), size(t))
	store(m, v, t, root)
	return hex.EncodeToString(m.b), ""
}

func decode(img string, root uint64, t D) (v interface{}, err string) {
	defer func() {
		if r := recover(); r != nil {
			if e, ok := r.(abiErr); ok {
				err = e.code
				return
			}
			err = fmt.Sprint("PANIC:", r)
		}
	}()
	b, e := hex.DecodeString(img)
	if e != nil {
		fail("PK_INTEROP_TYPE_MISMATCH")
	}
	m := &Mem{b: b}
	return load(m, root, t), ""
}

func readJSON(path string) D {
	raw, err := os.ReadFile(path)
	if err != nil {
		panic(err)
	}
	var d D
	if err := json.Unmarshal(raw, &d); err != nil {
		panic(err)
	}
	return d
}

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "usage: encode|decode|selftest vectors.json [images.json]")
		os.Exit(2)
	}
	vec := readJSON(os.Args[2])
	out := D{}
	switch os.Args[1] {
	case "encode":
		for _, x := range vec["valid"].([]interface{}) {
			v := x.(D)
			img, err := encode(v["value"], v["descriptor"].(D))
			if err != "" {
				out[v["id"].(string)] = D{"err": err}
			} else {
				out[v["id"].(string)] = D{"image": img, "root": 0}
			}
		}
	case "decode":
		imgs := readJSON(os.Args[3])
		all := append(vec["valid"].([]interface{}), vec["invalid"].([]interface{})...)
		for _, x := range all {
			v := x.(D)
			id := v["id"].(string)
			src, ok := imgs[id].(D)
			if !ok {
				continue
			}
			if _, bad := src["err"]; bad {
				out[id] = D{"err": "PRODUCER_FAILED"}
				continue
			}
			val, err := decode(src["image"].(string), uint64(src["root"].(float64)), v["descriptor"].(D))
			if err != "" {
				out[id] = D{"err": err}
			} else {
				out[id] = D{"ok": val}
			}
		}
	case "bench":
		// MC-034: per-operation lower+lift latency on the golden vectors.
		for _, x := range vec["valid"].([]interface{}) {
			v := x.(D)
			id := v["id"].(string)
			if id != "u32-max" && id != "record-point" && id != "record-doc" && id != "list-string" {
				continue
			}
			t := v["descriptor"].(D)
			n := 200000
			if id == "record-doc" {
				n = 50000
			}
			lat := make([]int64, n)
			for i := 0; i < n; i++ {
				t0 := time.Now()
				m := &Mem{}
				root := m.alloc(align(t), size(t))
				store(m, v["value"], t, root)
				_ = load(m, root, t)
				lat[i] = time.Since(t0).Nanoseconds()
			}
			sort.Slice(lat, func(a, b int) bool { return lat[a] < lat[b] })
			out[id] = D{"n": n, "p50_ns": lat[n/2], "p95_ns": lat[n*95/100], "p99_ns": lat[n*99/100]}
		}
	default:
		fmt.Fprintln(os.Stderr, "unknown mode")
		os.Exit(2)
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(out); err != nil {
		panic(err)
	}
}
