// MC-019/MC-011 real WebAssembly guest (Go -> wasip1/wasm, run under Node's V8).
//
// The guest owns its linear memory.  It exports the canonical-ABI entry points
// a component runtime would call: cabi_realloc, post_return, and functions that
// produce / consume values in the INV-12 canonical layout for
//   record entry { id: u32, name: string, tags: list<string> }
// The host (tools/wasm_host.mjs) lifts and lowers through the bounds-checked
// adapter in fixtures/js/inv12.mjs, directly over WebAssembly.Memory.
package main

import (
	"encoding/binary"
	"unsafe"
)

const arenaSize = 1 << 16

var arena [arenaSize]byte
var pos uint32
var liveAllocs int32
var postReturns int32

func base() uint32 { return uint32(uintptr(unsafe.Pointer(&arena[0]))) }

//go:wasmexport cabi_realloc
func cabiRealloc(oldPtr, oldSize, align, newSize uint32) uint32 {
	if oldPtr != 0 || oldSize != 0 {
		if newSize == 0 {
			liveAllocs--
			return 0
		}
		return 0 // growth unsupported: returns null, host must reject
	}
	p := (pos + align - 1) &^ (align - 1)
	if p+newSize > arenaSize {
		return 0xFFFFFFF0 // deliberately invalid; host must reject
	}
	pos = p + newSize
	liveAllocs++
	return base() + p
}

//go:wasmexport post_return
func postReturn() {
	postReturns++
	pos = 0
	liveAllocs = 0
}

//go:wasmexport live_allocs
func liveAllocations() int32 { return liveAllocs }

//go:wasmexport post_returns
func postReturnCount() int32 { return postReturns }

func put32(addr, v uint32) {
	binary.LittleEndian.PutUint32(arena[addr-base():], v)
}

func str(s string) (uint32, uint32) {
	p := cabiRealloc(0, 0, 1, uint32(len(s)))
	copy(arena[p-base():], s)
	return p, uint32(len(s))
}

//go:wasmexport produce
func produce() uint32 {
	root := cabiRealloc(0, 0, 4, 20)
	put32(root, 42)
	np, nl := str("guést-\U0001F980")
	put32(root+4, np)
	put32(root+8, nl)
	tags := cabiRealloc(0, 0, 4, 16)
	a, al := str("wasm")
	b, bl := str("go")
	put32(tags, a)
	put32(tags+4, al)
	put32(tags+8, b)
	put32(tags+12, bl)
	put32(root+12, tags)
	put32(root+16, 2)
	return root
}

//go:wasmexport produce_bad
func produceBad() uint32 {
	root := cabiRealloc(0, 0, 4, 20)
	put32(root, 1)
	put32(root+4, 0xFFFFFF00) // string pointer outside linear memory
	put32(root+8, 64)
	put32(root+12, 0)
	put32(root+16, 0)
	return root
}

//go:wasmexport consume
func consume(root uint32) uint32 {
	// returns id + total UTF-8 bytes of name and tags, computed from guest memory
	r := root - base()
	id := binary.LittleEndian.Uint32(arena[r:])
	total := binary.LittleEndian.Uint32(arena[r+8:])
	tp := binary.LittleEndian.Uint32(arena[r+12:]) - base()
	n := binary.LittleEndian.Uint32(arena[r+16:])
	for i := uint32(0); i < n; i++ {
		total += binary.LittleEndian.Uint32(arena[tp+8*i+4:])
	}
	return id*1000 + total
}

func main() {}
