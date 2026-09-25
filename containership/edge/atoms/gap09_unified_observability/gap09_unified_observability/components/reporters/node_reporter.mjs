// GAP09-CSP/1 reference reporter in JavaScript (non-Python cross-language check).
// Usage: node node_reporter.mjs <seed-hex-32-bytes> <envelope-json-file>
// Prints {"canonical": ..., "signature": hex, "public": hex}.
import { createPrivateKey, createPublicKey, sign } from "node:crypto";
import { readFileSync } from "node:fs";

function canon(v) {
  if (v === null) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error("non-finite");
    if (Object.is(v, -0)) throw new Error("negative zero");
    return JSON.stringify(v);            // ECMAScript Number::toString
  }
  if (typeof v === "string") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(canon).join(",") + "]";
  const keys = Object.keys(v).sort();    // default sort = UTF-16 code units
  return "{" + keys.map(k => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}";
}

const [seedHex, file] = process.argv.slice(2);
const env = JSON.parse(readFileSync(file, "utf8"));
const der = Buffer.concat([Buffer.from("302e020100300506032b657004220420", "hex"), Buffer.from(seedHex, "hex")]);
const key = createPrivateKey({ key: der, format: "der", type: "pkcs8" });
const text = canon(env);
const sig = sign(null, Buffer.from(text, "utf8"), key);
const pub = createPublicKey(key).export({ format: "der", type: "spki" }).subarray(-32);
process.stdout.write(JSON.stringify({ canonical: text, signature: sig.toString("hex"), public: pub.toString("hex") }));
